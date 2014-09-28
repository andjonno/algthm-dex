"""
worker.py

Worker module does the work of pulling a repository from the given url. Once the
repository is obtained, it is given to the indexer which carries out various
analysis on the codebase.

If any clone fails it is passed to the error handler where the appropriate
systems are informed. One possible error is a 404 from the request. If this
occurs, the repository should be striked. After a number of strikes, it may be
necessary to remove it from the rotation and black listed.
"""
from bson import ObjectId
from elasticsearch import ElasticsearchException
import traceback
import pika
from pika import exceptions
import json
from logger import logger
from indexer import Indexer
from cfg.loader import cfg
from core.exceptions.indexer import *
from urllib3.exceptions import ProtocolError
from core.db import MongoConnection
from datetime import datetime

logger = logger.get_logger('dex')
TIMEOUT = 4


def target(_id):
    """
    boot function
    """
    Worker(_id).run()


class Worker(object):

    def __init__(self, _id):
        """
        Downloads repositories with urls retrieved from the Queue
        Arguments:
            queue, Queue instance
            repo_location, string location to store repository
        """
        self.id = _id
        self.db_conn = MongoConnection().get_db()

    # Method continues until terminated by indexer
    def run(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=cfg.settings.mq.connection.host
        ))
        channel = connection.channel()
        channel.queue_declare(queue=cfg.settings.mq.queue_name,
                              durable=True)

        def callback(ch, method, properties, body):
            m = json.loads(body)
            with Indexer(self.id, m['id'], m['url']) as indexer:
                try:
                    indexer.load().index()

                except ExternalSystemException as err:
                    # should be investigated.
                    MongoConnection().get_db().system_errors.insert({
                        'exception': 'ExternalSystemError',
                        'message': str(err),
                        'timestamp': datetime.today(),
                        'task': 'indexing {}'.format(m['id'])
                    })

                except (RepositoryCloneFailure, StatisticsUnavailable,
                        IndexerDependencyFailure) as err:
                    # Repository specific failure
                    self.db_conn.repositories.update(
                        {
                            '_id': ObjectId(m['id'])
                        },
                        {
                            '$inc': {
                                'error_count': 1
                            },
                            '$set': {
                                'state': 0,
                                'comment': str(err)
                            }
                        },
                        multi=True
                    )

                except (ElasticsearchException, ProtocolError) as err:
                    # External system failure
                    raise ExternalSystemException('System error: {}'
                                                  .format(err))

                except OSError as err:
                    logger.error(err)

                except Exception as e:
                    print 'Worker failed ', e
                    traceback.print_exc()

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(callback, queue=cfg.settings.mq.queue_name)
        try:
            channel.start_consuming()
        except exceptions.ConnectionClosed:
            print 'worker#{} failed: MQ Connection Closed.'.format(self.id)

