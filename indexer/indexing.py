# Indexer,
# takes a repository url and checks out on the local file system. This module,.
# then performs a number of analysis on the repository. The results from this 
# is then searchable for users.

from shutil import rmtree
from os import makedirs
from time import sleep
from conf.logging.logger import logger

logger = logger.get_logger(__name__)


class Indexing(object):
    """Indexer analyses repositories and stores result in database"""

    def __init__(self, url, location):
        self.url = url
        self.location = location

    def __enter__(self):
        makedirs(self.location)
        return self

    def __exit__(self, type, value, traceback):
        rmtree(self.location)

    def index(self):
        logger.info("\033[1;36mIndexing\033[0m {}".format(self.url))
        sleep(8)
