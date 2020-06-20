SciDB-Py: Python Interface to SciDB
===================================

.. image:: https://img.shields.io/badge/SciDB-19.11-blue.svg
    :target: https://forum.paradigm4.com/t/scidb-release-19-11/2411

.. image:: https://img.shields.io/badge/arrow-0.16.0-blue.svg
    :target: https://arrow.apache.org/release/0.16.0.html

.. image:: https://travis-ci.org/Paradigm4/SciDB-Py.svg
    :target: https://travis-ci.org/Paradigm4/SciDB-Py

Warning
-------

Since SciDB-Py Release **16.9.1** (released in `September 2017`) the
library has been rewritten entirely from scratch. **16.9.1** and newer
versions are **not compatible** with the previous versions of the
library. The documentation for the previous versions is available at
`SciDB-Py documentation (legacy)
<http://scidb-py.readthedocs.io/en/v16.9-legacy/>`_. GitHub pull
requests are still accepted for the previous versions, but the code is
not actively maintained.


Version Information
-------------------

The major and minor version numbers of SciDB-Py track the major and
minor version of SciDB they are compatible with. For example SciDB-Py
``16.9.1``, ``16.9.2`` or ``16.9.10`` are all compatible with SciDB
``16.9.x``.

During SciDB ``16.9``, Shim (HTTP service for SciDB) transitioned from
query authentication to session authentication. SciDB-Py has been
updated to be compatible with the new Shim. Below is the compatibility
matrix between SciDB-Py and Shim:

===========  =====
SciDB-Py     Shim
===========  =====
``16.9.1``   query authentication (old Shim)
``16.9.2``   query authentication (old Shim)
``16.9.10``  session authentication (new Shim)
===========  =====

From ``16.9.10`` onwards only Shim with session authentication is
supported.


Requirements
------------

SciDB ``16.9`` or newer with Shim

Python ``2.7.x``, ``3.4.x``, ``3.5.x``, ``3.6.x``, ``3.7.x``, or newer.

Required Python packages::

  backports.weakref
  enum34
  numpy
  pandas
  pyarrow (see version requirements in setup.py)
  requests
  six


CentOS 6 and Red Hat Enterprise Linux 6
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CentOS ``6`` and Red Hat Enterprise Linux ``6`` come with Python
``2.6``. SciDB-Py requires Python ``2.7`` or newer (see above). The
default Python cannot be upgraded on these operating systems. Instead
a different Python version can be installed in parallel using
`Software Collections <https://www.softwarecollections.org/en/>`_. For
example, `here
<https://www.softwarecollections.org/en/scls/rhscl/python27/>`_ are
the instructions to install Python ``2.7`` using Software Collections.



Installation
------------

Install latest release::

  pip install scidb-py

Install development version from GitHub::

  pip install git+http://github.com/paradigm4/scidb-py.git


Documentation
-------------

See `SciDB-Py Documentation <http://paradigm4.github.io/SciDB-Py/>`_.
