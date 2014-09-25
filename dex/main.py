#!/usr/bin/env python
"""
Indexer module

Manages the multiprocess approach to indexing the database. This module spawns a
fixed number of worker process where each worker feeds repository urls fetched
from the queue. These are passed to the indexing object.

The worker is defined by worker.py which is the root execution of the process.
"""

import pika
import sys
import worker
import feeder
from shutil import rmtree
from time import sleep
from algthm.utils.file import dir_empty
from cfg.loader import cfg
from multiprocessing import Process
from logger import logger
from dex.core.db import MongoConnection
from dex.core.exceptions.indexer import IndexerBootFailure
from logging import CRITICAL, getLogger
from datetime import datetime

logger.setup_logging()
logger = logger.get_logger('dex')
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
            process = Process(target=target, args=(i + 1,))
            process.daemon = daemon
            process.start()
            workers.append(process)

            sys.stdout.write('\r')
            sys.stdout.write('> %s workers initialized' % (i + 1))
            sys.stdout.flush()
            sleep(cfg.settings.general.worker_cooling)

        except RuntimeError:
            pass

    print ' .. ok'
    return workers


def test_db_connection(db_conn):
    """
    Tests that the db connection is alive and well.
    """
    # TODO: implement mongo connection test
    return True


def test_mq_connection(mq_conn):
    """
    Tests that the mq connection is alive and well.
    """
    # TODO: implement mq conn test
    return True


def test_es_connection(es_conn):
    return es_conn.ping()


def cool_off(duration=3, char='*'):
    """
    Throws up a progress bar for the given duration.
    """
    interval = duration / 100.0
    for i in range(101):
        sys.stdout.write('\r')
        sys.stdout.write('\033[1;34m%-82s %d\033[0m' %
                         (char * (int(i * 0.82)), i))
        sys.stdout.flush()
        sleep(interval)

    print


def create_index_session(db_conn):
    """
    Creates the session in the database.
    :param db_conn: database connection
    :return: ObjectId for session
    """
    session_id = None
    try:
        # reset repositories states, error counts, etc..
        repositories = db_conn.repositories
        sessions = db_conn.sessions

        repositories.update({}, {'$set': {'error_count': 0,'state':
            feeder.STATE.get('waiting'), 'comment': ''}},
                              multi=True, upsert=True)
        session_id = sessions.insert({'start_time': datetime.today(), 'total':
            repositories.count()})

    except Exception:
        raise IndexerBootFailure('Failed to initialize session.')

    return session_id


def finish_session(db_conn, session_id):
    db_conn.sessions.update(
        {'_id': session_id},
        {
            '$set': {
                'finish_time': datetime.today()
            }
        },
        multi=True,
        upsert=True
    )


def prepare_workspace(workspace):
    ok = True
    try:
        rmtree(workspace)
        ok = True
    except OSError:
        pass  # already prepared
    return ok


def welcome(working_directory):
    welcome = """
        .'   .;.    _
   .-..'  .-.   `.,' '      DEX indexing module 0.0.3. Copyright 2014 Algthm.
  :   ; .;.-'   ,'`.        Working Directory: [working_directory]
  `:::'`.`:::'-'    `._.    Log: [log_location]
"""
    print '\033[1;34m{}\033[0m'\
        .format(welcome.replace('[log_location]', '/Users/jon/tmp/dex.log')
                .replace('[working_directory]', working_directory))


def main():
    working_directory = cfg.settings.general.directory
    welcome(working_directory)

    while 1:
        try:
            print '> preparing workspace ..',
            if prepare_workspace(cfg.settings.general.directory):
                print 'ok'

            print '> connecting to Mongo ..',
            db_conn = MongoConnection().get_db()
            if db_conn:
                print 'done'
            else:
                raise IndexerBootFailure("Could not connect to DB.")

            print '> connecting to MQ @ {} ..'\
                .format(cfg.settings.mq.connection.host),
            try:
                mq_conn = pika.BlockingConnection(pika.ConnectionParameters(
                    host=cfg.settings.mq.connection.host
                ))
                if mq_conn:
                    print 'done'
            except pika.exceptions.AMQPConnectionError:
                raise IndexerBootFailure("Could not connect to MQ.")

            print 'letting connections establish before testing.'
            cool_off(cfg.settings.general.cooling)

            print '> testing DB connection and schema ..',
            if test_db_connection(db_conn):
                print 'ok'
            else:
                raise IndexerBootFailure('Algthm schema not defined in DB.')

            print '> preparing indexing session ..',
            session_id = create_index_session(db_conn)
            if session_id:
                print 'ID:{}'.format(session_id)

            print '> testing MQ connection ..',
            if test_mq_connection(mq_conn):
                print 'ok'
                print '> purging MQ ..',
                mq_conn.channel().queue_delete(
                    queue=cfg.settings.mq.indexing_q_name)
                print 'ok'
            else:
                raise IndexerBootFailure("MQ connection failed.")

            workers = initialize_workers(cfg.settings.general.workers,
                                         worker.target)
            print 'letting workers establish.'
            cool_off(cfg.settings.general.cooling)

            print '> initialize feeder ..',
            fdr = feeder.Feeder(session_id, db_conn, mq_conn)
            if fdr:
                print 'ok'
            else:
                raise IndexerBootFailure("Could not start the feeder.")

            #-------------------------------------------------------------------
            #   All Checks Complete - Run
            #-------------------------------------------------------------------
            print '> running ...'
            fdr.feed_manager()

            # Presence of contents in the working directory denotes there are a
            # number of workers still processes jobs. Wait for directory to be
            # empty before continuing.
            print '> finalising ..',
            while not dir_empty(working_directory):
                print '.',
                sleep(5)
            print 'done!'

            cool_off(1)
            fdr.report_failures()

            # session.set(dict(finish_time=strftime('%Y-%m-%d %H:%M:%S'))).save()
            print '> session finished'
            finish_session(db_conn, session_id)

            # debug
            # TODO: take out this line for prod
            break
            db_conn.close()

            print '> rebooting ..'
            for p in enumerate(workers):
                try:
                    p[-1].terminate()
                except RuntimeError:
                    pass

        except IndexerBootFailure as e:
            print e
            print "exiting .."
            break

if __name__ == "__main__":
    main()


