"""
Common string operations
"""

from re import sub


def normalize_string(text):
    """
    Removes strange characters and multiple spaces sequences from text.
    """
    text = sub("[^A-z0-9@\._'\" :/]", " ", text)
    text = sub(" +", " ", text)
    text = sub("^ ", "", text)
    return text