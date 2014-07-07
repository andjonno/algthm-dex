#!/usr/bin/env python
"""
Indexer module

Manages the multiprocess approach to indexing the database. This module spawns a fixed number of worker
process where each worker feeds repository urls fetched from the queue. These are passed to the indexing object.

The worker is defined by worker.py which is the root execution of the process.
"""

from conf.config_loader import config_loader
from multiprocessing import Process
from indexer import worker, feeder
from conf.logging.logger import logger
from lib.db import get_connection
import pika
import sys
from os import path
from time import sleep
from mysql.connector import Error
from indexer.core.exceptions.indexer import IndexerBootFailure
from logging import CRITICAL, getLogger
from shutil import rmtree
from lib.models.base_model import BaseModel


logger.setup_logging('indexer')
logger = logger.get_logger(__name__)
pika_logger = getLogger('pika')
pika_logger.setLevel(CRITICAL)


def initialize_workers(num_workers, target, daemon=True):
    """
    Initializes the worker processes.
    """
    workers = []
    process = None

    print '> initializing {} workers ..'.format(num_workers),

    for i in range(num_workers):
        try:
            process = Process(target=target, args=(i+1,))
            process.daemon = daemon
            process.start()
            workers.append(process)

            sys.stdout.write('\r')
            sys.stdout.write('> %s workers initialized' % (i + 1))
            sys.stdout.flush()
            sleep(config_loader.cfg.indexer['worker_cooling'])

        except RuntimeError:
            pass

    print ' .. ok'
    return workers


def test_db_connection(db_conn):
    """
    Tests that the db connection is alive and well.
    """
    test_stmt = "SELECT count(*) FROM information_schema.tables WHERE table_schema = '{}';".format(
        config_loader.cfg.database['database'])
    curs = db_conn.cursor()
    is_good = None
    try:
        curs.execute(test_stmt)
        row = curs.fetchone()
        is_good = row[0] != 0
        curs.close()
    except Error as err:
        is_good = False

    return is_good


def test_mq_connection(mq_conn):
    """
    Tests that the mq connection is alive and well.
    """
    # TODO: implement mq conn test
    return True


def cool_off(duration=3, char='-'):
    """
    Throws up a progress bar for the given duration.
    """
    interval = duration / 100.0
    for i in range(101):
        sys.stdout.write('\r')
        sys.stdout.write("\033[1;34m%-82s %d\033[0m" % (char * (int(i * 0.82)), i))
        sys.stdout.flush()
        sleep(interval)

    print


def create_index_session(db_conn):
    """
    Executes a storedproc to clean the database for this session.
    """
    _id = 0
    try:
        cursor = db_conn.cursor()
        cursor.callproc('prepare_index_session')
        cursor.fetchone()
        for result in cursor.stored_results():
            for row in result:
                _id = row[0]
                break
        cursor.close()
    except Error:
        pass

    return BaseModel('index_sessions', dict(id=_id)).fetch()


def prepare_workspace(workspace):
    ok = False
    try:
        rmtree(workspace)
        ok = True
    except OSError:
        pass # already prepared
    return ok


if __name__ == "__main__":
    with open(config_loader.cfg.indexer['welcome']) as welcome:
        print welcome.read().replace('[version]',
            config_loader.cfg.indexer['version']).replace(
                '[log_location]',
                path.join(path.dirname(path.abspath(__file__)), 'logs', 'indexer.log'))
    print '> booting DEX'

    while 1:
        try:
            print '> preparing workspace ..',
            if prepare_workspace(config_loader.cfg.indexer['directory']):
                print 'ok'

            print '> connecting to DB @ {} ..'.format(config_loader.cfg.database['host']),
            db_conn = get_connection()
            if db_conn:
                print 'done'
            else:
                raise IndexerBootFailure("Could not connect to DB.")

            print '> connecting to MQ @ {} ..'.format(config_loader.cfg.mq['connection']['host']),
            mq_conn = pika.BlockingConnection(pika.ConnectionParameters(
                host=config_loader.cfg.mq['connection']['host']
            ))
            if mq_conn:
                mq_conn.channel().queue_delete(queue=config_loader.cfg.mq['indexing_q_name'])
                print 'done'
            else:
                raise IndexerBootFailure("Could not connect to MQ.")

            print 'letting connections establish before testing.'
            cool_off(config_loader.cfg.indexer['cooling'])

            print '> testing DB connection and schema ..',
            if test_db_connection(db_conn):
                print 'ok'
            else:
                raise IndexerBootFailure("Algthm schema not defined in DB.")

            print '> preparing indexing session ..',
            session = create_index_session(db_conn)
            if session:
                print 'session id #{}'.format(session.get('id'))

            print '> testing MQ connection ..',
            if test_mq_connection(mq_conn):
                print 'ok'
            else:
                raise IndexerBootFailure("MQ connection failed.")

            workers = initialize_workers(config_loader.cfg.indexer['workers'], worker.target)
            print 'letting workers establish.'
            cool_off(config_loader.cfg.indexer['cooling'])

            print '> initialize feeder ..',
            fdr = feeder.Feeder(session, db_conn, mq_conn)
            if fdr:
                print 'ok'
            else:
                raise IndexerBootFailure("Could not start the feeder.")



            print '> running ...'
            fdr.feed_manager()

            cool_off(10)
            fdr.report_failures()

            print '> rebooting ..'
            db_conn.close()
            for p in enumerate(workers):
                try:
                    p[-1].terminate()
                except RuntimeError:
                    pass

        except IndexerBootFailure as e:
            print e
            break





