"""
Indexer, takes a repository url and checks out on the local file system. This module then performs a number of analysis
on the repository. The results from this is then searchable for users.
"""

import re
import time
from datetime import datetime
from os import makedirs, devnull
from os import path
from shutil import rmtree
from subprocess import call
import pygit2
from algthm.utils.file import match_in_dir
from algthm.utils.string import normalize_string
from bson.objectid import ObjectId
from feeder import STATE
from cfg.loader import cfg
from core.db import MongoConnection
from core.exceptions.indexer import IndexerDependencyFailure
from core.exceptions.indexer import RepositoryCloneFailure
from core.exceptions.indexer import StatisticsUnavailable
from core.exceptions.indexer import ExternalSystemException
from core.model.languages import Languages
from core.model.result import Result
from logger import logger
from elasticsearch import Elasticsearch, ElasticsearchException


logger = logger.get_logger('dex')
CLOC_OUTPUT_FILE = 'cloc.yaml'


class Indexer:
    """Indexer analyses repositories and stores result in database"""

    def __init__(self, worker_id, id, url):
        """
        Initialize an indexer with id and url.

        :param worker_id: int worker ID
        :param id: int repository ID
        :param url: string repository url
        :return: None
        """
        self.db_conn = MongoConnection().get_db()
        self.worker_id = worker_id
        self.id = id
        self.url = url
        self.name = url.split('/')[-1]
        self.location = path.join(cfg.settings.general.directory, '{}@{}'.format(self.name, self.worker_id))

        self.repo = None
        self.language_statistics = None
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
        except OSError:
            pass
        self.repo = None
        self.language_statistics = None
        self.name = None
        self.readme = None

    def load(self):
        """
        Downloads the repository to the file system.
        """
        logger.info('\033[1;33mCloning\033[0m {}'.format(self.url))
        try:
            pygit2.clone_repository(self.url, self.location)
            self.repo = pygit2.init_repository(self.location)
        except pygit2.GitError, err:
            raise RepositoryCloneFailure(('Unable to clone repository {}, with error: {}'.format(self.url, err)))

        return self

    def index(self):
        """
        Begin the indexing transaction. A number of steps are carried out once the repository has been cloned on to the
        file system.
        """
        repo_model = self.db_conn.repositories.find_one({'_id': self.id})

        self.__start_time = time.time()
        try:
            self.extract_language_statistics()
            self.extract_readme()
            self.process_results()

        except (RepositoryCloneFailure, StatisticsUnavailable, IndexerDependencyFailure) as err:
            # Log failure to database.
            self.db_conn.repositories.update(
                {
                    '_id': ObjectId(self.id)
                },
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

        except ElasticsearchException as err:
            # External dependency error, should be reported.
            raise ExternalSystemException('Elastic Search error: {}'.format(err))

        except OSError as err:
            logger.error(err)

    def process_results(self):
        """
        Store the results in the repo model, then add job to queue for later indexing.
        :return: None
        """
        index_duration = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.__start_time))
        self.db_conn.repositories.update(
            {
                '_id': ObjectId(self.id)
            },
            {
                '$set': {
                    'state': STATE.get('complete'),
                    'indexed_on': datetime.today(),
                    'index_duration': index_duration
                }
            },
            upsert=False,
            multi=True
        )

        # Aggregate results
        self.result = Result(self.name, self.url)
        self.result.set_statistics(self.language_statistics)
        self.result.set_fulltext(readme=self.readme)

        es = Elasticsearch()
        es.index(index='repositories', doc_type='json', body=self.result.serialize(), id=str(self.id))

        logger.info('\033[1;32mCompleted\033[0m {} in {}'.format(self.url, index_duration))

    #-------------------------------------------------------------------------------------------------------------------
    #   DO_ METHODS
    #   Routines below do various indexing operations.
    #-------------------------------------------------------------------------------------------------------------------

    def extract_language_statistics(self):
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
            call(['cloc', self.location, '--yaml', '--report-file={}'.format(path.join(self.location, CLOC_OUTPUT_FILE))],
                 stdout=dn, stderr=dn)
            dn.close()
        except OSError:
            raise IndexerDependencyFailure('`cloc` application was not found on this machine.')

        if not path.isfile(path.join(self.location, CLOC_OUTPUT_FILE)):
            logger.info('\033[1;31mEmpty\033[0m {}, skipping ..'.format(self.url))
            raise StatisticsUnavailable('Empty repository')
        else:
            self.language_statistics = Languages(path.join(self.location, CLOC_OUTPUT_FILE), self.name)

    def extract_readme(self):
        """
        Searchable text currently includes README files. They contain the rundown of the codebase; we're primarily
        interested in its purpose. A user search for "ruby web framework", could match a line in the rails readme:
            'Ruby on Rails is a "web framework" written in "ruby"'
        Similarly, works for the absolute case too: "rails web framework". Beautiful thing..
        """
        try:
            r = re.compile(r'^README', re.IGNORECASE)
            readme_location = match_in_dir(r, self.location)[0]

            f = open(readme_location, 'r')
            self.readme = normalize_string(f.read())
            f.close()
        except Exception:
            pass # no readme

    def extract_license(self):
        """
        License information may be something to display in the application results. This would be useful for
        organisations who are conscientious of the open source projects they use in their products or development.
        """
        #TODO: Get license information
        pass

































