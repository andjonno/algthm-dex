"""
Class provides access to the discovery configuration.
Confuguration is accessible by directly access properties on the 
config object.
"""

import os
import yaml

CONFIG_FILE = 'core.yaml'


class ConfigLoader(object):

    def __init__(self):
        location = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        config = self.__load_config(location)

        self.database = BindConfig(config['database'])
        self.github = BindConfig(config['github'])


    def __load_config(self, location):
        with open(location) as file_obj:
            config = yaml.load(file_obj)
        return config

class BindConfig(object):
    def __init__(self, config):
        for (k, v) in config.iteritems():
            setattr(self, k, v)

config_loader = ConfigLoader()
