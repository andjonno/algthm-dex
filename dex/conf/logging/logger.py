"""
Logging module which wraps the python built-in logging framework.

To enable logging, initialize a logging object. This object should then be fetched from this logging module as
required.
"""

import logging.config
import pkg_resources
import yaml


class Logger(object):
    def __init__(self):
        pass

    def get_logger(self, name):
        return logging.getLogger(name)

    def setup_logging(self, name):
        stream = pkg_resources.resource_stream(__name__, ("{}_logging.yaml".format(name)))
        config = yaml.load(stream)
        logging.config.dictConfig(config)

# Initialize logging config
logger = Logger()