"""
Feeder retrieves urls from the repository store and adds them to the MQ when necessary.
"""

import time
import pika
from cfg.loader import cfg
from math import pow
from mysql.connector import Error
from json import dumps
from logger import logger
from logging import getLogger, CRITICAL
from requests import get
from datetime import datetime


logger = logger.get_logger('dex')
requests_logger = getLogger('requests')
requests_logger.setLevel(CRITICAL)


STATE = dict(
    waiting=0,
    processing=1,
    complete=2
)
UPDATE_STMT         = "UPDATE repositories SET state = '{}' WHERE id IN ({});"
SELECT_TO_REPORT    = "SELECT id, comment FROM repositories WHERE error_count >= {};"
INSERT_REPORTED     = "INSERT INTO on_report (repo_id, session_id, comment) VALUES {};"


class Feeder:
    """
    Shared properties
    """
    MAX_RETRIES = cfg.settings.mq.max_retries
    MQ_USER = cfg.settings.mq.connection.username
    MQ_PASS = cfg.settings.mq.connection.password
    FEED_SIZE = cfg.settings.mq.feed_size
    FEED_BUFFER = FEED_SIZE * 0.2
    FEED_SM_CONSTANT = cfg.settings.mq.smoothing_constant
    FEED_MAX_SLEEP = cfg.settings.mq.max_sleep
    WORKERS = cfg.settings.general.workers
    sleep = 10
    demand = 0
    forecast = 0
    error_sq = 0

    __last_feed = None
    __stop_feeding = False


    def __init__(self, session_id, db_conn, mq_conn):
        """
        Establish connection with database and MQ
        """
        self.session_id = session_id
        self.db_conn = db_conn
        self.mq_conn = mq_conn
        self.chan = self.mq_conn.channel()
        self.chan.queue_declare(queue=cfg.settings.mq.indexing_q_name, durable=True)
        self.system = None

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

        items = []

        try:
            repositories = self.db_conn.repositories
            results = repositories.find(
                {
                    'error_count': {
                        '$lt': self.MAX_RETRIES
                    },
                    '$or': [
                        {
                            'indexed_on': {
                                '$lt': datetime.today()
                            }
                        },
                        {
                            'indexed_on': None
                        }
                    ],
                    'state': 0
                },
                limit=self.FEED_SIZE
            ).sort([('activity', -1)])

            for repo in results:
                items.append((repo['_id'], repo['url']))

            # update session
            session = self.db_conn.sessions.find_one({'_id': self.session_id})
            session['feed'] = len(items) if not session.get('feed') else session.get('feed') + len(items)
            self.db_conn.sessions.save(session)

            # update selected repo status' to 'processing=1'
            if len(items):
                ids = [x[0] for x in items]
                self.__set_flag_processing(ids)

                # push to the MQ
                for _id, url in items:
                    self.__add_to_queue(_id, url)
            else:
                logger.info('\033[1;37mFeeding exhausted.\033[0m')
                self.__stop_feeding = True

        except Error as err:
            # TODO: implement error handling
            print err

    def feed_manager(self):
        """
        Monitors the rate of consumption of the queue, and determines the appropriate time to add more urls to the
        queue. Exponential smoothing is used here to assist in determining the appropriate time to repopulate the queue.
        """
        messages = None
        sleep = 0
        # once feeder has no remaining repositories to populate, `sleep_remaining` will contain the total sleep time
        # until the workers theoretically should be finished.
        sleep_remaining  = 0
        # timeout will be incremented until it reaches `sleep_remaining/10`
        timeout = 1

        while timeout:
            data = get('http://localhost:15672/api/queues/%2f/index_queue?'
                       'columns=backing_queue_status.avg_ack_egress_rate,messages',
                       auth=(self.MQ_USER, self.MQ_PASS)).json()

            messages = data['messages']
            self.demand = data['backing_queue_status']['avg_ack_egress_rate']
            if self.forecast:
                self.error_sq = pow(self.demand - self.forecast, 2)
                self.forecast += self.FEED_SM_CONSTANT * (self.demand - self.forecast)
            else:
                self.forecast = self.demand if self.demand > 0 else 1

            if messages <= self.FEED_BUFFER:
                if not self.__stop_feeding:
                    self.feed()
                    messages += self.FEED_SIZE
                else:
                    sleep_remaining = messages / self.forecast
                    timeout = int(sleep_remaining / self.FEED_MAX_SLEEP)

            # determine sleep time required to get to buffer
            sleep = (messages - (self.FEED_BUFFER if messages > self.FEED_BUFFER else 0)) / self.forecast
            self.sleep = self.FEED_MAX_SLEEP if sleep > self.FEED_MAX_SLEEP else sleep

            self.__status()
            time.sleep(self.sleep)

    def report_failures(self):
        """
        Method gets all repositories that failed to be indexed and places them on report.
        """
        failures = list()
        try:
            # get failures and construct the insert statement
            result = self.db_conn.repositories.find({'error_count': {'$gte': self.MAX_RETRIES}})

            for failure in result:
                failures.append(failure)

            if len(failures) > 0:
                logger.info('Reporting {} failures for session#{}'.format(len(failures), self.session_id))
                for failure in failures:
                    self.db_conn.repositories.update(
                        {
                            '_id': failure.get('_id')
                        },
                        {
                            '$set': {
                                'on_report': True,
                                'comment': failure.get('comment')
                            }
                        },
                        upsert=True,
                        multi=True
                    )

                fmt = "\033[1;31mReported\033[0m - {} {}"
                for failure in failures:
                    logger.info(fmt.format(failure.get('_id'), failure.get('comment')))

        except Error as err:
            print err

    #-------------------------------------------------------------------------------------------------------------------
    #   HELPERS
    #-------------------------------------------------------------------------------------------------------------------

    def __set_flag_processing(self, ids):
        """
        Sets the list of repositories to 'processing' in the database. Should be called immediately after the FEEDER
        STMT is executed.
        """
        prepared = UPDATE_STMT.format(STATE['processing'], ','.join("{}".format(n) for n in ids))

        # insert to db
        for id in ids:
            self.db_conn.repositories.update({'_id': id}, {
                '$set': {'state': STATE.get('processing')}
            }, multi=True, upsert=False)

    def __add_to_queue(self, _id, url):
        """
        Adds the url to the queue
        """
        payload = dumps(dict(
            id=str(_id),
            url=url
        ))
        self.chan.basic_publish(
            exchange='',
            routing_key=cfg.settings.mq.indexing_q_name,
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

    def __status(self):
        session = self.db_conn.sessions.find_one({'_id': self.session_id})
        progress = (session.get('feed') / session.get('total') if session.get('total') != 0 else 1)
        repos_remaining = int(session.get('total') - session.get('total') * progress)
        repos_remaining = repos_remaining if repos_remaining >= 0 else 0
        time_rmg = time.strftime('%H:%M:%S', time.gmtime(repos_remaining /
                                                         (self.forecast if self.forecast >= 1 else 1)))

        d = {
            'Index Rate': ("{}/{}".format(self.demand, self.forecast)),
            'Square Error': self.error_sq,
            'Progress': progress * 100,
            'Repositories Remaining': repos_remaining,
            'Time Remaining': time_rmg
        }
        fmt = '{0:>40}: {1:<10}'
        for k,v in d.iteritems():
            logger.info(fmt.format(k,v))


