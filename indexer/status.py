"""
Allows for querying the indexing process.
"""

from lib.models.base_model import BaseModel

def index_progress():
    """
    Returns the percentage completion of the index session.
    """
    system = BaseModel('system', dict(sys='default'), id_col='sys').fetch()
    ip = system.get('index_progress')
    total = system.get('repository_count')
    return (ip / (total * 1.0), system)