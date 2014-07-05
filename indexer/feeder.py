"""
Feeder retrieves urls from the repository store and adds them to the MQ when necessary.
"""

import sys
import time
import pika
from conf.config_loader import config_loader
from math import pow
from lib.models.base_model import BaseModel
from mysql.connector import Error
from json import dumps
from conf.logging.logger import logger
from requests import get
from indexer import status
from datetime import datetime


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
SELECT_TO_REPORT = "SELECT id, url FROM repositories WHERE error_count >= {};"
INSERT_REPORTED = "INSERT INTO on_report (repo_id) VALUES {};"


class Feeder:
    """
    Shared properties
    """
    MAX_RETRIES = config_loader.cfg.mq['max_retries']
    MQ_USER = config_loader.cfg.mq['connection']['username']
    MQ_PASS = config_loader.cfg.mq['connection']['password']
    WORKERS = config_loader.cfg.indexer['workers']
    FEED_SIZE = config_loader.cfg.mq['feed_size']
    FEED_BUFFER = FEED_SIZE * 0.2
    FEED_SM_CONSTANT = config_loader.cfg.mq['smoothing_constant']
    FEED_MAX_SLEEP = config_loader.cfg.mq['max_sleep']
    sleep = 10
    demand = 0
    forecast = 0
    error_sq = 0

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
        prepared = FEEDER_STMT.format(STATE['waiting'], self.FEED_SIZE, self.MAX_RETRIES)
        items = []

        try:
            cursor = self.db_conn.cursor()
            cursor.execute(prepared)
            if cursor.rowcount > 0:
                logger.info("Feeding MQ ..")
                for (_id, url) in cursor:
                    items.append((_id, url))
                ids = [i[0] for i in items]
                self.__set_flag_processing(ids)
                for _id, url in items:
                    self.__add_to_queue(_id, url)
            else:
                logger.info('No more repositories left to feed ..')
                self.__stop_feeding = True
            cursor.close()

        except Error as err:
            # TODO: implement error handling
            print err

    def feed_manager(self):
        """
        Monitors the rate of consumption of the queue, and determines the appropriate time to add more urls to the
        queue. Exponential smoothing is used here to assist in determining the appropriate time to repopulate the queue.
        """
        complete = False
        messages = None
        sleep = 0
        # once feeder has no remaining repositories to populate, `sleep_remaining` will contain the total sleep time
        # until the workers theoretically should be finished.
        sleep_remaining  = 0
        # timeout will be incremented until it reaches `sleep_remaining/10`
        timeout = 1

        self.__status_header()

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
                    complete = True

            # determine sleep time required to get to buffer
            sleep = (messages - (self.FEED_BUFFER if messages > self.FEED_BUFFER else 0)) / self.forecast
            self.sleep = self.FEED_MAX_SLEEP if sleep > self.FEED_MAX_SLEEP else sleep

            self.__status()
            time.sleep(self.sleep)

        # Queue is empty, workers are still occupied. Theoretically, the number of jobs/messages left is equal
        # to the number of workers. Therefore, compute the sleep time.
        time.sleep(self.WORKERS / self.forecast)
        print


    def report_failures(self):
        """
        Method gets all repositories that failed to be indexed and places them on report.
        """
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(SELECT_TO_REPORT.format(self.MAX_RETRIES))
            self.db_conn.commit()

            # get failures and construct the insert statement
            print
            print '  {} failures reported'.format(cursor.rowcount)
            failures = []
            if cursor.rowcount > 0:
                for _id, url in cursor:
                    failures.append((_id, url))
            items = ",".join("({})".format(i[0]) for i in failures)
            cursor.close()

            cursor = self.db_conn.cursor()
            cursor.execute(INSERT_REPORTED.format(items))
            self.db_conn.commit()
            cursor.close()

            b_fmt = "  \033[1;37m{0:8}\033[0m \033[1;37m{1:100}\033[0m"
            fmt = "- {0:<8} {1:<100}"
            headers = b_fmt.format("ID", "Url")
            print headers
            for _id, url in failures:
                print fmt.format(_id, url)

            print

        except Error as err:
            print err



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

    def __add_to_queue(self, id, url):
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


    def __status_header(self):
        b_fmt = "  \033[1;37m{0:18}\033[0m \033[1;37m{1:12}\033[0m \033[1;37m{2:12}\033[0m \033[1;37m{3:12}\033[0m "\
                "\033[1;37m{4:12}\033[0m"
        headers = b_fmt.format("Rate(m/s) D/F", "Error(sq)", "Progress(%)", "Repos rmg", "Time rmg(est)")
        print headers


    def __status(self):
        """
        Displays the indexing process.
        """
        progress = status.index_progress()
        fmt = "- {0:<18} {1:<12} {2:<12} {3:<12} {4:<12}"
        system = progress[-1]
        repos_rmg = system.get('repository_count') - system.get('index_progress') - system.get('repository_error_count')
        try:
            time_rmg = time.strftime('%H:%M:%S', time.gmtime(repos_rmg / self.forecast))
        except ValueError:
            time_rmg = "--:--:--"

        data = fmt.format("{} / {}".format(
            round(self.demand, 4),
            round(self.forecast, 4)),
            round(self.error_sq, 4),
            int(progress[0] * 100),
            repos_rmg,
            time_rmg)
        print data

