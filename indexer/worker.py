"""
worker.py

Worker module does the work of pulling a repository from the given url. Once
the repository is obtained, it is given to the indexer which carries out 
various analysis on the codebase.

If any clone fails it is passed to the error handler where the appropriate 
systems are informed. One possible error is a 404 from the request. If this 
occurs, the repository should be striked. After a number of strikes, it may
be necessary to remove it from the rotation and black listed.
"""

from os import path
from Queue import Empty
from conf.logging.logger import logger
from indexer.indexing import Indexing

logger = logger.get_logger(__name__)
TIMEOUT = 4


class Worker(object):

    queue = None

    def __init__(self, queue, repo_location):
        """Downloads repositories with urls retrieved from the Queue"""
        self.queue = queue
        self.repo_location = repo_location

    # Method continues until terminated by dispatch
    def run(self):
        while 1:
            try:
                # `get` returns a tuple, (num, 'url')
                url = self.queue.get(True, TIMEOUT)[-1]
                location = path.join(self.repo_location, url.split('/')[-1])

                # Let the indexer do its magic
                with Indexing(url, location) as indexer:
                    indexer.index()

                self.queue.task_done()
            
            except Empty:
                # get from queue timeout
                # TODO: handle timeout
                pass
            
            except RuntimeError as e:
                logger.error('{}'.format(e))

