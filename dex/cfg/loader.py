#!/usr/bin/env python
"""
loader.py

A singleton class providing simple access to configurations.

**Example**

    host = cgf_loader.cfg.database['host']

"""

import os
import yaml
from missile.lib import constants
import bunch


class Loader:
    def __init__(self):
        location = os.path.join(os.path.dirname(__file__), constants.CONFIG_FILE)
        with open(location) as fp:
            self.settings = bunch.Bunch.fromDict(yaml.load(fp))


cfg = Loader()
