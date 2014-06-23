#!/usr/bin/env python
"""
Indexer module

Manages the multiprocess approach to indexing the discovery database. This module spawns a fixed number of worker
process where each worker feeds repository urls fetched from the queue. These are passed to the indexing object.

The worker is defined by worker.py which is the root execution of the process.
"""

from multiprocessing import Process
from indexer.queue import Queue
from indexer.worker import Worker
from conf.logging.logger import logger
from shutil import rmtree

logger.setup_logging("indexer")
logger = logger.get_logger(__name__)

VERSION = "0.0.1"
WORKERS = 4
REPO_LOCATION = '/tmp/repositories'


# Spawner for Worker initialization
def spawner(queue, repo_location):
    Worker(queue, repo_location).run()

def spawn_queue():
    Queue()

# Cleans up the checkout workspace. Should be done at the beginning and end 
# of this system.
def cleanup_workspace():
    logger.info("Cleaning workspace {}".format(REPO_LOCATION))
    try:
        rmtree(REPO_LOCATION)
    except:
        # already clean
        pass


class Dispatch(object):
    
    processes = []
    spawner = None
    queue = None

    def __init__(self, spawner, queue):
        self.spawner = spawner
        self.queue = queue

    def start(self):
        logger.info(('spawning {} workers'.format(WORKERS)))

        for x in range(WORKERS):
            try:
                self.processes.append(Process(target=self.spawner, 
                    args=(self.queue, REPO_LOCATION)))
                self.processes[x].daemon = True
                self.processes[x].start()
            
            except RuntimeError:
                # TODO: handle error appropriately
                pass


if __name__ == "__main__":
    logger.info(('Starting Dispatch {}'.format(VERSION)))
    cleanup_workspace()

    # The index queue provides itself 
    queue = Queue()
    dispatch = Dispatch(spawner, queue.queue)
    dispatch.start()

    while 1:
        queue.populate()

    # Wait until all tasks retreived from queue, then repopulate
    queue.queue.join()

    
    # System terminal from here..

    logger.info('Shutting down Dispatch engine..')
    logger.info('Killing workers..')
    for p in enumerate(dispatch.processes):
        try:
            p[-1].terminate()
        except RuntimeError:
            pass

    cleanup_workspace()

