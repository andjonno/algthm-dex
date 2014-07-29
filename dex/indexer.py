"""
Indexer, takes a repository url and checks out on the local file system. This module then performs a number of analysis
on the repository. The results from this is then searchable for users.
"""

import pygit2
import re
import time
from datetime import datetime
from os import makedirs, devnull
from os.path import join, isfile
from shutil import rmtree
from subprocess import call
from feeder import STATE
from cfg.loader import cfg
from core.db import MongoConnection
from core.exceptions.indexer import IndexerDependencyFailure
from core.exceptions.indexer import RepositoryCloneFailure
from core.exceptions.indexer import StatisticsUnavailable
from core.repository_statistics import RepositoryStatistics
from logger import logger
from algthm.utils.file import match_in_dir
from algthm.utils.string import normalize_string
from bson.objectid import ObjectId


logger = logger.get_logger('dex')
CLOC_OUTPUT_FILE = 'cloc.yaml'


class Indexer:
    """Indexer analyses repositories and stores result in database"""

    def __init__(self, w_id, _id, url):
        """
        Arguments,
            url - string, url of repository
            location - string, location on local file system
        """
        self.db_conn = MongoConnection().get_db()
        self.w_id = w_id
        self._id = _id
        self.url = url
        self.name = url.split('/')[-1]
        self.location = join(cfg.settings.general.directory, "{}_{}".format(self.name, self.w_id))

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
        try:
            rmtree(self.location)
        except:
            pass
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
        repo_model = self.db_conn.repositories.find_one({'_id': self._id})

        self.__start_time = time.time()
        try:
            # Load onto filesystem
            self.load()
            # Generate repository statistics
            self.do_stats()
            # Extract Readme
            self.do_readme()

            # If control reaches here, indexing was successful. Update the repository model.
            self.process_results()

        except (RepositoryCloneFailure, StatisticsUnavailable, IndexerDependencyFailure) as err:
            self.db_conn.repositories.update(
                {'_id': ObjectId(self._id)},
                {
                    '$inc': {
                        'error_count': 1
                    },
                    '$set': {
                        'state': STATE.get('waiting'),
                        'comment': str(err)
                    }
                },
                multi=True
            )

        except OSError as err:
            logger.error(err)

    def process_results(self):
        """
        Store the results in the repo model, then add job to queue for later indexing.
        :return: None
        """
        index_duration = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.__start_time))
        self.db_conn.repositories.update(
            {'_id': ObjectId(self._id)},
            { '$set': {
                  'state': STATE.get('complete'),
                  'indexed_on': datetime.today(),
                  'index_duration': index_duration
            }},
            upsert=False,
            multi=True
        )

        logger.info("\033[1;32mCompleted\033[0m {} in {}".format(self.url, index_duration))

    #-------------------------------------------------------------------------------------------------------------------
    #   DO_ METHODS
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
            raise StatisticsUnavailable("Empty repository")
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

































