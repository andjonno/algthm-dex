"""
Loader class for database connection tasks.
"""

__author__ = 'andjonno'


from conf.config_loader import config_loader
import mysql.connector
from mysql.connector import errorcode


config = config_loader.cfg.database


def get_connection():
    return mysql.connector.connect(
        user=config['username'],
        password=config['password'],
        host=config['host'],
        database=config['database'],
        buffered=True,
        autocommit=True
    )

