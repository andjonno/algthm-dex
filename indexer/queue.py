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

        self.items = [
            'https://github.com/mojombo/grit',
            'https://github.com/wycats/merb-core',
            'https://github.com/mojombo/god',
            'https://github.com/vanpelt/jsawesome',
            'https://github.com/wycats/jspec',
            'https://github.com/defunkt/exception_logger',
            'https://github.com/defunkt/ambition',
            'https://github.com/technoweenie/restful-authentication',
            'https://github.com/technoweenie/attachment_fu',
            'https://github.com/-andrew-/AwesomeBot',
            'https://github.com/-funroll-loops/potion',
            'https://github.com/-kostya-/yaChat',
            'https://github.com/-SFT-Clan/big-brother-bot',
            'https://github.com/0--/leelib',
            'https://github.com/0--key/OvivoStaff',
            'https://github.com/0-0-/BankBlock',
            'https://github.com/0-0-/javaTetris',
            'https://github.com/0-0-0/a',
            'https://github.com/0-0-Bram/spacebuild',
            'https://github.com/0-07/Adblock-Light-for-Chrome',
            'https://github.com/0-07/FwTester',
            'https://github.com/0-0Flash0-0/java-intro-2014',
            'https://github.com/0-0Flash0-0/PHP-Minecraft-Query',
            'https://github.com/0-14N/app-crawlers',
            'https://github.com/0-14N/BabelDroid'
        ]

        self.populate()

    def populate(self):
        for i in enumerate(self.items):
            self.queue.put(i)
