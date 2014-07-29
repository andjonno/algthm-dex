"""
Logging singleton. Ensures logging is consistent across the entire application. Logger configuration is found in
the `conf/` directory. This logger subclasses the python `logging` module.
"""

__author__ = 'Jon Scanes <me@jscanes.com>'

import logging
import logging.config
import pkg_resources
import yaml


class Logger:
    def __init__(self):
        pass

    def get_logger(self, name):
        return logging.getLogger(name)

    def setup_logging(self):
        stream = pkg_resources.resource_stream(__name__, 'logging.yaml')
        config = yaml.load(stream)
        logging.config.dictConfig(config)

# Initialize logger config
logger = Logger()