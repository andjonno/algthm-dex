"""
Feeder retrieves urls from the repository store and adds them to the MQ when necessary.
"""

import time
import pika
from conf.config_loader import config_loader
from lib.db.commands import connect
from mysql.connector import Error
from json import dumps
from conf.logging.logger import logger
from requests import get

logger = logger.get_logger(__name__)

STATE = dict(
    waiting=0,
    processing=1,
    complete=2
)
FEEDER_STMT = \
    "SELECT id, url FROM repositories WHERE id IN (SELECT id FROM repositories ORDER BY activity_rating DESC) AND " \
    "state = '{0}' AND indexed_on < NOW() AND error_count < {2} ORDER BY indexed_on ASC LIMIT {1};"
UPDATE_STMT = "UPDATE repositories SET state = '{}' WHERE id IN ({});"
SELECT_TO_REPORT = "SELECT id FROM repositories WHERE error_count >= {};"


class Feeder:
    """
    Shared properties
    """
    FEED_SIZE = config_loader.cfg.mq['feed_size']
    BUFFER = FEED_SIZE * 0.2
    MAX_RETRIES = config_loader.cfg.mq['max_retries']
    MQ_USER = config_loader.cfg.mq['connection']['username']
    MQ_PASS = config_loader.cfg.mq['connection']['password']

    FEED_SM_CONSTANT = config_loader.cfg.mq['smoothing_constant']
    sleep = 10
    d = 0
    f = 0

    __last_feed = None
    __stop_feeding = False


    def __init__(self, db_conn, mq_conn):
        """
        Establish connection with database and MQ
        """
        self.db_conn = db_conn
        self.mq_conn = mq_conn
        self.chan = self.mq_conn.channel()
        self.chan.queue_declare(queue=config_loader.cfg.mq['indexing_q_name'], durable=True)


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mq_conn.close()

    def feed(self):
        """
        Fetches the next 100 urls from the repository store and puts them on the queue. Prevents from over feeding
        itself.
        """
        if self.__last_feed and (time.time() - self.__last_feed < 10):
            return
        else:
            self.__last_feed = time.time()
        prepared = FEEDER_STMT.format(STATE['waiting'], self.FEED_SIZE, self.MAX_RETRIES)
        ids = []

        try:
            cursor = self.db_conn.cursor()
            cursor.execute(prepared)
            if cursor.rowcount > 0:
                logger.info("Feeding MQ ..")
                for (_id, url) in cursor:
                    ids.append(_id)
                    self.add_to_queue(_id, url)
                self.__set_flag_processing(ids)
            else:
                logger.info('No more repositories left to feed ..')
                print '0 repositories left to feed .. letting workers finish.'
                self.__stop_feeding = True
            cursor.close()

        except Error as err:
            # TODO: implement error handling
            print err

    def monitor_feed(self):
        """
        Monitors the rate of consumption of the queue, and determines the appropriate time to add more urls to the
        queue. Exponential smoothing is used here to assist in determining the appropriate time to repopulate the queue.
        """
        msgs = None

        while 1:
            data = get('http://localhost:15672/api/queues/%2f/index_queue?'
                       'columns=backing_queue_status.avg_ack_egress_rate,messages',
                       auth=(self.MQ_USER, self.MQ_PASS)).json()
            msgs = data['messages']

            # Forecast the future egress val
            self.d = data['backing_queue_status']['avg_ack_egress_rate']
            if self.f:
                self.f += self.FEED_SM_CONSTANT * (self.d - self.f)
            else:
                self.f = self.d if self.d > 0 else 1

            if msgs <= self.BUFFER:
                if not self.__stop_feeding:
                    self.feed()
                    msgs = self.FEED_SIZE
                else:
                    print 'done!'
                    break

            # determine sleep time required to get to buffer
            self.sleep = (msgs - self.BUFFER) / self.f
            self.sleep = 10 if self.sleep > 10 else self.sleep
            time.sleep(self.sleep)

    def report_failures(self):
        """
        Method gets all repositories that failed to be indexed and places them on report.
        """
        print 'reporting failures'

    """ ----------------------------------------------------------------------------------------------------------------
        HELPERS
    """

    def __set_flag_processing(self, ids):
        """
        Sets the list of repositories to 'processing' in the database. Should be called immediately after the FEEDER
        STMT is executed.
        """
        prepared = UPDATE_STMT.format(STATE['processing'], ','.join("{}".format(n) for n in ids))
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(prepared)
            self.db_conn.commit()
            cursor.close()
        except Error as err:
            print err

    def add_to_queue(self, id, url):
        """
        Adds the url to the queue
        """
        payload = dumps(dict(
            id=id,
            url=url
        ))
        self.chan.basic_publish(
            exchange='',
            routing_key=config_loader.cfg.mq['indexing_q_name'],
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

