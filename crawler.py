#!/usr/bin/env python 
"""
Discovery Module

This module extracts git repository urls from our whitelisted domains. Each 
source has specific requirements. Github provides an api which provides 
information for all public repositories so the implementation for this will 
differ from other sources. This module populates the repository database and 
terminates leaving indexing to be carried out by the indexing module.
"""

from crawler.github import github
from conf.logging.logger import logger

if __name__ == "__main__":
    logger.setup_logging("crawler")
    github.__run()