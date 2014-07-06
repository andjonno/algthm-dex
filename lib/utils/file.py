"""
Some utilities for working with file and directory structures.
"""

from os import walk
from os.path import abspath, join
from fnmatch import filter
from re import sub
from bs4 import BeautifulSoup
from markdown import markdown


def locate(pattern, root_path):
    """
    Find all instances of pattern in a directory.
    Arguments
        pattern, unix like bash regex
        root_path, string, search structure
    Returns a generator.
    """
    for path, dirs, files in walk(abspath(root_path)):
        for filename in filter(files, pattern):
            yield join(path, filename)


def md_to_txt(file_obj):
    """
    Given a markdown file, converts to html and extracts all pure text from that html.
    Most reliable way of getting valuable text from markdown file.
    """
    try:
        text = file_obj.read()
        html = markdown(text)
        return ''.join(BeautifulSoup(html).findAll(text=True))
    except Exception:
        return ''

