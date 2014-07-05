"""
Indexer,
takes a repository url and checks out on the local file system. This module then performs a number of analysis on the
repository. The results from this is then searchable for users.
"""

from os.path import join
import pygit2
import random
from os import makedirs
from shutil import rmtree
from os.path import basename, isfile
from subprocess import call
from indexer.core.exceptions.indexer import IndexerDependencyFailure
from indexer.core.exceptions.indexer import RepositoryCloneFailure
from indexer.core.exceptions.indexer import StatisticsUnavailable
from conf.config_loader import config_loader
from core.repository_statistics import RepositoryStatistics
from conf.logging.logger import logger
from lib.utils.file import locate, md_to_txt
from lib.utils.string import normalize_string
from lib.models.base_model import BaseModel

logger = logger.get_logger(__name__)
CLOC_OUTPUT_FILE = 'cloc.yaml'


class Indexing:
    """Indexer analyses repositories and stores result in database"""

    repo = None
    repo_stats = None
    name = None

    def __init__(self, id, url):
        """
        Arguments,
            url - string, url of repository
            location - string, location on local file system
        """
        self.id = id
        self.url = url
        self.name = url.split('/')[-1]
        self.location = join(config_loader.cfg.indexer['directory'], self.name)

    def debug(self):
        repo = BaseModel('repositories', dict(id=self.id)).fetch()
        repo.set('state', '2')
        if random.random() * 100 > 50:
            repo.set('error_count', repo.get('error_count') + 1)
            repo.set('state', '0')
        repo.save()

    def __enter__(self):
        #makedirs(self.location)
        return self

    def __exit__(self, type, value, traceback):
        #rmtree(self.location)
        self.repo = None
        self.repo_stats = None
        self.name = None

    def load(self):
        """
        Downloads the repository to the file system.
        """
        logger.info("\033[1;36mDownloading\033[0m {}".format(self.url))
        try:
            pygit2.clone_repository(self.url, self.location)
        except pygit2.GitError, err:
            raise RepositoryCloneFailure(("Unable to clone repository {}, with error: {}".format(self.url, err)))
        self.repo = pygit2.init_repository(self.location)

    def index(self):
        """
        Begin the indexing transaction.
        """
        self.load()
        logger.info("\033[1;36mIndexing\033[0m {}".format(self.url))
        try:
            self.generate_stats()
            self.repo_stats = RepositoryStatistics(join(self.location, CLOC_OUTPUT_FILE), self.name)
            print self.repo_stats
        except StatisticsUnavailable:
            """proceed without stats"""
            pass

        self.generate_readme()
        print self.readme

    """ ----------------------------------------------------------------------------------------------------------------
        GENERATE_ METHODS
        Routines below do various indexing operations.
    """

    def generate_stats(self):
        """
        Method calls a subprocess 'cloc' to do some stats on the directory. The result of this is saved to
        `CLOC_OUTPUT_FILE` in the repository location. The results are in yaml format, which will be later read. `cloc`
        understand language specific syntax for a vast number of languages; it knows what language a file is written,
        and to a further extent, what a comment looks like in this language. From this information, we can determine
        its main language, eg, ruby framework, js, etc.

        Throws StatisticsUnavailable, if repo contains no code
        """
        try:
            call(["cloc", self.location, "--yaml", "--report-file={}".format(join(self.location, CLOC_OUTPUT_FILE))])
        except OSError:
            raise IndexerDependencyFailure("`cloc` application was not found on this machine.")

        if not isfile(join(self.location, CLOC_OUTPUT_FILE)):
            logger.error("Repository {} does not contain any code. Skipping stats..".format(self.name))
            raise StatisticsUnavailable()

    def generate_readme(self):
        """
        Searchable text currently includes README files. They contain the rundown of the codebase; we're primarily
        interested in its purpose. A user search for "ruby web framework", could match a line in the rails readme:
            'Ruby on Rails is a "web framework" written in "ruby"'
        Similarly, works for the absolute case too: "rails web framework". Beautiful thing..
        """
        readme = ""
        rms = locate("README*", self.location)
        for rm in rms:
            with open(rm) as file:
                readme += normalize_string(md_to_txt(file))

        self.readme = readme

    def generate_licensing(self):
        """
        License information may be something to display in the application results. This would be useful for
        organisations who are conscientious of the open source projects they use in their products or development.
        """
        #TODO: Get license information
        pass

































