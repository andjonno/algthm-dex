"""
Some utilities for working with file and directory structures.
"""

from os import walk, listdir
from os.path import abspath, join
import fnmatch


def locate(pattern, root_path):
    """
    Find all instances of pattern in a directory.
    Arguments
        pattern, unix like bash regex
        root_path, string, search structure
    Returns a generator.
    """
    for path, dirs, files in walk(abspath(root_path), topdown=True):
        for filename in fnmatch.filter(files, pattern):
            yield join(path, filename)

def match_in_dir(r_exp, dre):
    """
    Match all f
    """
    path = []
    try:
        path = [join(dre, f) for f in filter(r_exp.match, listdir(dre))]
    except Exception as e:
        pass
    return path
