"""
Github Crawler

Polls the github api retrieving all public repository urls. Once found, they are stored in the
algthm.repositories.
"""

from urlparse import urljoin
from conf.config_loader import config_loader
from core.models.base_model import BaseModel
from core.db.commands import connect
from conf.logging.logger import logger
import requests
import mysql.connector

logger = logger.get_logger(__name__)

class GitHub(object):

    API_BASE = 'https://api.github.com/'
    URL_KEY = 'html_url'
    ENDPOINTS = dict(
        repositories=urljoin(API_BASE, 'repositories')
    )

    #	Flag to stop processing
    run = False

    # The repositories endpoint takes in a since paramter which it will return
    # results from this point. It refers to the repository ID. It is paginated
    # so we must call the API each time with the last repository ID we've seen.
    # This value is fetched from the `state` table algthm database as it is 
    # updated upon every api response.
    system = None

    conn = None
    cursor = None

    def __init__(self):
        self.config = config_loader.github
        self.conn = connect()

    def __exit__(self):
        self.cursor.close()

    def run(self):
        self.cursor = self.conn.cursor()
        self.system = BaseModel('system', dict(id=1)).fetch()

        while self.run:
            auth_header = {"Authorization": ("token {}".format(self.config.authorization))}
            res = requests.get(self.construct_url(), headers=auth_header)
            self.process_response(res)

    def construct_url(self):
        url = "{}?{}={}".format(self.ENDPOINTS['repositories'], 'since', self.system.get('discovery_since'))
        return url

    def process_response(self, response):
        if response.status_code != 404 or response.status_code != 500:
            repos = response.json()
            if len(repos) != 0:
                for repo in repos:
                    self.insert_to_db(repo[self.URL_KEY])

                self.system.set('discovery_since', repos[-1]['id']).save()
            else:
                #	Stop running on empty response
                self.run = False

        logger.info("\033[1;36mCrawling\033[0m {} repositories discovered ..".format(self.system.get('discovery_since')))

    def insert_to_db(self, git_url):
        sql = "INSERT INTO repositories (url) VALUES ('%s')" % git_url
        try:
            self.cursor.execute(sql)
            self.conn.commit()
        except mysql.connector.Error as err:
            print err

github = GitHub()
