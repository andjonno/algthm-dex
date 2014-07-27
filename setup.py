#!/usr/bin/env python

from setuptools import setup, find_packages
import os


base_dir = os.path.dirname(os.path.abspath(__file__))

setup(name='dex-indexer',
    version='1.0.0',
    description='Core Business Service for Trail.',
    author='-',
    author_email='-',
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'mysql-connector-python',
        'pyyaml',
        'pygit2',
        'pika'
    ],
    package_data={
        '': ['*.yaml']
    },
    test_suite='nose.collector',
    tests_require=['nose'],
    entry_points={
        'console_scripts': [
            'dex = dex.dex:main'
        ]
    }
)
