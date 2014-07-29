"""
Utilities for classes and objects.
"""

def singleton(cls):
    """
    Singleton decorator. Makes the decorated class a singleton.
    """
    instances = {}
    def get_instance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return get_instance