"""
Loader class for database connection tasks.
"""

from conf.config_loader import config_loader
import mysql.connector
from mysql.connector import errorcode

config = config_loader.database

def connect():
	conn = None
	try:
		conn = mysql.connector.connect(
			user=config.username, 
			password=config.password, 
			host=config.host, 
			database=config.database,
			buffered=True
		)
	except mysql.connector.Error as err:
		print err
	return conn
