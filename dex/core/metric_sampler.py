#!/usr/bin/env python

import pygit2
import datetime
from metric import Metric
from sector import Sector
from dex.core.model.contributor import Contributor


ONE_WEEK = 604800
RESOLUTION = ONE_WEEK


class MetricSampler:
    """
    Metrics extracts repository specific features such as additions/deletions,
    contributor activity, number of lines etc. Given a pygit2.Repository handle
    this module will produce a model ready for database insertion.

    Metrics information has a time associated with it. The difference between
    2 recorded metrics is known as the resolution. The default resolution is a
    period of 1 week. When sampling a repository, the number of metrics produced
    is determined by since/resolution. As resolution gets smaller the number of
    records produced increases. We must take data storage into consideration
    when setting the resolution. 1 week is ok. 52 metrics per Repository/year.
    """

    def __init__(self, repository):
        """
        Initialize Metric
        :param repository: pygit2.Repository
        """

        if repository and type(repository) != pygit2.Repository:
            raise ValueError('pygit2.Repository required.')

        # Current features extracted are:
        self.r = repository
        self.head = self.r.get(self.r.head.target)
        self.__load_commits()
        self.__sectors = []
        self.__metrics = []
        self.__contributors = []

    def sample_sectors(self):
        """
        Runs the process to sample the repository.
        :return:
        """
        self.__sectors = self.__generate_sectors()

        for sector in self.__sectors:
            commits_in_sector = sector.get_objects()
            commits_count = len(commits_in_sector)

            if commits_count:
                m = Metric()

                m.commit_count = commits_count
                last_commit = commits_in_sector[commits_count - 1]

                m.commit = commits_in_sector[0]
                score = self.__score(commits_in_sector[0].id.hex,
                                     last_commit.id.hex, commits_count)
                m.activity = score[0]
                m.additions = score[1]
                m.deletions = score[2]
                m.timestamp = datetime.datetime.fromtimestamp(
                    last_commit.commit_time)

                self.__metrics.append(m)

    def sample_contributors(self):
        """
        Extracts all unique authors from the Commit objects.
        :return:
        """

        # Store in hashmap
        contributors = dict()
        for commit in self.commits:
            try:
                contributors[commit.author.email]["count"] += 1
            except KeyError:
                contributors[commit.author.email] = dict(
                    name=commit.author.name,
                    count=1
                )

        for k in contributors.iterkeys():
            self.__contributors.append(Contributor(name=contributors[k]["name"],
                                            email=k,
                                            count=contributors[k]["count"]))
        return self.__contributors

    def get_metrics(self):
        return self.__metrics

    def get_contributors(self):
        return self.__contributors

    def __score(self, a, b, commits_for_sector):
        """
        Determines the activity score. Basic algorithm
            commits per day * changes since last week.
        Also determines additions and deletions which are needed in the
        calculation.
        :return: tuple
        """
        additions = 0
        deletions = 0
        try:
            diff = self.r.diff(a, b)

            for patch in diff:
                additions += patch.additions
                deletions += patch.deletions

            activity = 1 / commits_for_sector + (additions + deletions)

            return activity, additions, deletions
        except ValueError:
            return 0, 0, 0

    def __total_commits(self):
        return len(self.commits)

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    def __load_commits(self):
        """
        Loads all commits in the repository into a list. Sets the pointer to
        zero.
        :return: None
        """
        self.commits = list()
        for _commit in self.r.walk(self.r.head.target,
                                   pygit2.GIT_SORT_TOPOLOGICAL):
            self.commits.append(_commit)

        self.commits = sorted(self.commits, key=lambda x: x.commit_time,
                              reverse=True)

    def __generate_sectors(self):
        """
        Returns all commits from HEAD to given commit based on the resolution.
        :return: list
        """
        sectors = list()
        sector = None
        x = 0
        num_commits = len(self.commits)
        while x < num_commits:
            commit = self.commits[x]
            if not sector:
                sector = Sector(commit.commit_time,
                                commit.commit_time - RESOLUTION)

            if sector.add_object(commit, commit.commit_time):
                x += 1
            else:
                sectors.append(sector)
                sector = None

        # Add last sector
        sectors.append(sector)

        return sectors
