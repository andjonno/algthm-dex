

from datetime import datetime


class Metric:
    """
    Metric is a model object to hold repository features at a specific point in
    time. This time is based on the resolution in the MetricSampler.
    """
    def __init__(self):
        self.commit = None
        self.timestamp = 0
        self.additions = 0
        self.deletions = 0
        self.activity = 0
        self.commit_count = 0

    def __str__(self):
        return '{},{:=6} additions, {:=6} deletions, {:=6} commits, {:=6} activity @ {}'.format(self.commit.id, self.additions, -self.deletions,
                           self.commit_count, self.activity, self.timestamp)

    def __dict__(self):
        return dict(
            commit=self.commit.id,
            additions=self.additions,
            deletions=self.deletions,
            commit_count=self.commit_count,
            activity=self.activity,
            timestamp=self.timestamp
        )