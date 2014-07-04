"""
The indexing process will tend to avoid repositories with less activity
and favour those with more, regular indexing.

This queue implements that functionality to the indexer.

When requested, the queue will return a list of urls that it thinks 
are due to be indexed. Currently, this is based on date however a future 
version will implement a smarter queueing system.
"""

from multiprocessing import JoinableQueue


class Queue(object):

    queue = None
    items = []

    def __init__(self):
        self.queue = JoinableQueue()
        self.populate()

    def populate(self):
        # TODO: pull from database
        for i in enumerate(self.items):
            self.queue.put(i)
