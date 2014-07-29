"""
worker.py

Worker module does the work of pulling a repository from the given url. Once the repository is obtained, it is given to
the indexer which carries out various analysis on the codebase.

If any clone fails it is passed to the error handler where the appropriate systems are informed. One possible error is
a 404 from the request. If this occurs, the repository should be striked. After a number of strikes, it may be necessary
to remove it from the rotation and black listed.
"""

import pika
import json
from logger import logger
from indexer import Indexer
from cfg.loader import cfg

logger = logger.get_logger('dex')
TIMEOUT = 4


def target(id):
    """
    boot function
    """
    Worker(id).run()


class Worker(object):

    def __init__(self, _id):
        """
        Downloads repositories with urls retrieved from the Queue
        Arguments:
            queue, Queue instance
            repo_location, string location to store repository
        """
        self.id = _id


    # Method continues until terminated by indexer
    def run(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=cfg.settings.mq.connection.host)
        )
        channel = connection.channel()
        channel.queue_declare(queue=cfg.settings.mq.indexing_q_name, durable=True)

        def callback(ch, method, properties, body):
            m = json.loads(body)
            with Indexer(self.id, m['id'], m['url']) as idxr:
                idxr.index()

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(callback, queue=cfg.settings.mq.indexing_q_name)
        channel.start_consuming()

