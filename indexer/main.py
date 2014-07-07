"""
Indexer, takes a repository url and checks out on the local file system. This module then performs a number of analysis
on the repository. The results from this is then searchable for users.
"""

import pygit2
import re
import time
from os import makedirs, devnull
from os.path import join, isfile
from shutil import rmtree
from subprocess import call
from indexer.feeder import STATE
from indexer.core.exceptions.indexer import IndexerDependencyFailure
from indexer.core.exceptions.indexer import RepositoryCloneFailure
from indexer.core.exceptions.indexer import StatisticsUnavailable
from conf.config_loader import config_loader
from core.repository_statistics import RepositoryStatistics
from conf.logging.logger import logger
from lib.utils.file import match_in_dir
from lib.utils.string import normalize_string
from lib.models.base_model import BaseModel


logger = logger.get_logger(__name__)
CLOC_OUTPUT_FILE = 'cloc.yaml'


class Indexing:
    """Indexer analyses repositories and stores result in database"""


    def __init__(self, w_id, id, url):
        """
        Arguments,
            url - string, url of repository
            location - string, location on local file system
        """
        self.w_id = w_id
        self.id = id
        self.url = url
        self.name = url.split('/')[-1]
        self.location = join(config_loader.cfg.indexer['directory'], "{}_{}".format(self.name, self.w_id))

        self.repo = None
        self.repo_stats = None
        self.name = None
        self.readme = None

        self.__start_time = None

    def __enter__(self):
        try:
            rmtree(self.location)
        except OSError:
            pass # already removed
        makedirs(self.location)
        return self

    def __exit__(self, type, value, traceback):
        rmtree(self.location)
        self.repo = None
        self.repo_stats = None
        self.name = None
        self.readme = None

    def load(self):
        """
        Downloads the repository to the file system.
        """
        logger.info("\033[1;33mCloning\033[0m {}".format(self.url))
        try:
            pygit2.clone_repository(self.url, self.location)
        except pygit2.GitError, err:
            raise RepositoryCloneFailure(("Unable to clone repository {}, with error: {}".format(self.url, err)))
        self.repo = pygit2.init_repository(self.location)

    def index(self):
        """
        Begin the indexing transaction. A number of steps are carried out once the repository has been cloned on to the
        file system.
        """
        repo_model = BaseModel('repositories', dict(id=self.id)).fetch()
        logger.info("Beginning index on {}".format(self.url))
        self.__start_time = time.time()
        index_duration = 0
        try:
            # Load onto filesystem
            self.load()
            # Generate repository statistics
            self.do_stats()
            # Extract Readme
            self.do_readme()
            # If control reaches here, indexing was successful
            index_duration = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.__start_time))
            repo_model.set(dict(state=STATE['complete'], index_duration=index_duration)).save()
            logger.info("\033[1;32mCompleted\033[0m {} in {}".format(self.url, index_duration))
        except (RepositoryCloneFailure, StatisticsUnavailable, IndexerDependencyFailure) as err:
            repo_model.set(dict(error_count=repo_model.get('error_count')+1, state='0')).save()
        except OSError as err:
            logger.error(err)

    #-------------------------------------------------------------------------------------------------------------------
    #   GENERATE_ METHODS
    #   Routines below do various indexing operations.
    #-------------------------------------------------------------------------------------------------------------------

    def do_stats(self):
        """
        Method calls a subprocess 'cloc' to do some stats on the directory. The result of this is saved to
        `CLOC_OUTPUT_FILE` in the repository location. The results are in yaml format, which will be later read. `cloc`
        understand language specific syntax for a vast number of languages; it knows what language a file is written,
        and to a further extent, what a comment looks like in this language. From this information, we can determine
        its main language, eg, ruby framework, js, etc.

        Throws StatisticsUnavailable, if repo contains no code
        """
        try:
            dn = open(devnull, 'w')
            call(["cloc", self.location, "--yaml", "--report-file={}".format(join(self.location, CLOC_OUTPUT_FILE))],
                 stdout=dn, stderr=dn)
            dn.close()
        except OSError:
            raise IndexerDependencyFailure("`cloc` application was not found on this machine.")

        if not isfile(join(self.location, CLOC_OUTPUT_FILE)):
            logger.info("\033[1;31mEmpty\033[0m {}, skipping ..".format(self.url))
            raise StatisticsUnavailable()
        else:
            self.repo_stats = RepositoryStatistics(join(self.location, CLOC_OUTPUT_FILE), self.name)

    def do_readme(self):
        """
        Searchable text currently includes README files. They contain the rundown of the codebase; we're primarily
        interested in its purpose. A user search for "ruby web framework", could match a line in the rails readme:
            'Ruby on Rails is a "web framework" written in "ruby"'
        Similarly, works for the absolute case too: "rails web framework". Beautiful thing..
        """
        try:
            r = re.compile(r'^README', re.IGNORECASE)
            readme_loc = match_in_dir(r, self.location)[0]

            f = open(readme_loc, 'r')
            self.readme = normalize_string(f.read())
            f.close()
        except Exception:
            pass # no readme

    def do_licensing(self):
        """
        License information may be something to display in the application results. This would be useful for
        organisations who are conscientious of the open source projects they use in their products or development.
        """
        #TODO: Get license information
        pass

































