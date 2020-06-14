#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import scidbpy


NAME = 'scidb-py'
DESCRIPTION = 'Python library for SciDB'
LONG_DESCRIPTION = open('README.rst').read()
AUTHOR = 'Rares Vernica'
AUTHOR_EMAIL = 'rvernica@gmail.com'
DOWNLOAD_URL = 'http://github.com/Paradigm4/SciDB-Py'
LICENSE = 'AGPL-3.0'
VERSION = scidbpy.__version__

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    download_url=DOWNLOAD_URL,
    license=LICENSE,
    packages=['scidbpy'],
    install_requires=[
        'backports.weakref',
        'enum34',
        'numpy',
        'pandas',
        'pyarrow==0.16.0',
        'requests',
        'six',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Database :: Front-Ends',
        'Topic :: Scientific/Engineering',
    ],
)
