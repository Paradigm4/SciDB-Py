"""Quick Start
===========

Install the package with::

  $ pip install scidb-py

Connect to SciDB and run a query:

>>> from scidbpy import connect
>>> db = connect('http://localhost:8080')
>>> db.iquery('store(build(<x:int64>[i=0:2], i), foo)')

Download data from SciDB:

>>> db.arrays.foo[:]
   i    x
0  0  0.0
1  1  1.0
2  2  2.0

Upload data to SciDB and create an array:

>>> import numpy
>>> ar = db.input(upload_data=numpy.arange(3)).store()
>>> print(ar)
... # doctest: +ELLIPSIS
py_..._1

Run a query with chained operators and download the resulting array:

>>> db.join(ar, 'foo').apply('j', ar.i + 1)[:]
   i  x  x_1  j
0  0  0  0.0  1
1  1  1  1.0  2
2  2  2  2.0  3

Operators can also be composed:

>>> db.apply(db.join(ar, 'foo'), 'j', ar.i + 1)[:]
   i  x  x_1  j
0  0  0  0.0  1
1  1  1  1.0  2
2  2  2  2.0  3

Cleanup:

>>> db.remove(db.arrays.foo)
>>> del ar


Requirements
============

SciDB ``16.9`` or newer with Shim

Python ``2.7.x``, ``3.4.x``, ``3.5.x``, ``3.6.x`` or newer.

Required Python packages::

  backports.weakref
  enum34
  numpy
  pandas
  requests
  six


Installation
============

Install latest release::

  $ pip install scidb-py

Install development version from GitHub::

  $ pip install git+http://github.com/paradigm4/scidb-py.git


Connect to SciDB
================

Connect to SciDB using :func:`connect()<scidbpy.db.connect>`:

>>> from scidbpy import connect
>>> db = connect()
>>> db = connect('http://localhost:8080')

``connect()`` is aliased to the constructor of the
:class:`DB<scidbpy.db.DB>` class. See :meth:`DB()<scidbpy.db.DB>` for
the complete set of arguments that can be provided to
``connect``. ``http://localhost:8080`` is the default connection URL
is none is provided.

Display information about the ``db`` object:

>>> db
DB('http://localhost:8080', None, None, None, False, None, False, 256, False)

>>> print(db)
scidb_url         = http://localhost:8080
scidb_auth        = None
http_auth         = None
verify            = None
admin             = False
namespace         = None
use_arrow         = False
result_size_limit = 256
no_ops            = False


Advanced Connection
-------------------

Provide `Shim <https://github.com/Paradigm4/shim>`_ credentials:

>>> db = connect(http_auth=('foo', 'bar'))

>>> db
... # doctest: +NORMALIZE_WHITESPACE
DB('http://localhost:8080',
   None,
   ('foo', PASSWORD_PROVIDED),
   None,
   False,
   None,
   False,
   256,
   False)

>>> print(db)
scidb_url         = http://localhost:8080
scidb_auth        = None
http_auth         = ('foo', PASSWORD_PROVIDED)
verify            = None
admin             = False
namespace         = None
use_arrow         = False
result_size_limit = 256
no_ops            = False

To prompt the user for the password, use:

>>> import getpass
>>> db = connect(http_auth=('foo', getpass.getpass()))
... # doctest: +SKIP
Password:


Use SSL:

>>> db_ssl = connect('https://localhost:8083', verify=False)

>>> print(db_ssl)
scidb_url         = https://localhost:8083
scidb_auth        = None
http_auth         = None
verify            = False
admin             = False
namespace         = None
use_arrow         = False
result_size_limit = 256
no_ops            = False

See Python `requests <http://docs.python-requests.org/en/master/>`_
library `SSL Cert Verification
<http://docs.python-requests.org/en/master/user/advanced/
#ssl-cert-verification>`_ section for details on the ``verify``
argument. ``verify=False`` disables SSL certificate
verification. Warnings about the unverified HTTPS requests are
displayed. The warnings can be disabled as well by either setting
``PYTHONWARNINGS="ignore:Unverified HTTPS request"`` in the
environment before starting Python or by doing:

>>> import requests
>>> requests.packages.urllib3.disable_warnings(
...   requests.packages.urllib3.exceptions.InsecureRequestWarning)


Use SSL and SciDB credentials:

>>> db_ssl = connect(
...   'https://localhost:8083', scidb_auth=('foo', 'bar'), verify=False)

>>> print(db_ssl)
scidb_url         = https://localhost:8083
scidb_auth        = ('foo', PASSWORD_PROVIDED)
http_auth         = None
verify            = False
admin             = False
namespace         = None
use_arrow         = False
result_size_limit = 256
no_ops            = False


When using the ``iquery`` SciDB client, the ``--admin`` flag is
available for opening a higher-priority session. This flag is also
available in SciDB-Py and can be set at connection time (see `SciDB
Documentation <https://paradigm4.atlassian.net/wiki/spaces/scidb>`_
for details on the effects of the flag). By default this flag is set
to ``False``:

>>> db_admin = connect(admin=True)

>>> print(db_admin)
scidb_url         = http://localhost:8080
scidb_auth        = None
http_auth         = None
verify            = None
admin             = True
namespace         = None
use_arrow         = False
result_size_limit = 256
no_ops            = False


By default, the ``connect`` function queries SciDB for the list of
available operators. This list is used for easy access to the SciDB
operators, see the *SciDB Operators* section below. As a consequence
the connection to SciDB is verified and a small delay might
occur. This behavior can be disabled using the ``no_ops=True``
parameter. Accessing the SciDB operators as described in *SciDB
Operators* will not be possible until the ``load_ops()`` function is
called on the ``DB`` instance:

>>> db_no_ops = connect(no_ops=True)
>>> db_no_ops.scan
Traceback (most recent call last):
    ...
AttributeError: Operators not loaded. Run 'load_ops()' or use \
'no_ops=False' (default) at connection time (constructor)

No query has been issued to SciDB yet.

>>> db_no_ops.load_ops()
>>> db_no_ops.scan
... # doctest: +NORMALIZE_WHITESPACE
Operator(db=DB('http://localhost:8080',
               None,
               None,
               None,
               False,
               None,
               False,
               256,
               False),
         name='scan',
         args=[])


SciDB Arrays
============

SciDB arrays can be accessed using ``DB.arrays``:

>>> db = connect()
>>> db.iquery('store(build(<x:int64>[i=0:2], i), foo)')

>>> dir(db.arrays)
... # doctest: +ALLOW_UNICODE
[u'foo']

>>> dir(db.arrays.foo)
... # doctest: +ALLOW_UNICODE
[u'i', u'x']

>>> db.arrays.foo[:]
   i    x
0  0  0.0
1  1  1.0
2  2  2.0

>>> db.arrays['foo'][:]
   i    x
0  0  0.0
1  1  1.0
2  2  2.0

To get the schema of an array, we can use the ``schema`` utility
function:

>>> print(db.arrays.foo.schema())
foo<x:int64> [i=0:2:0:1000000]

>>> db.arrays.foo.schema().pprint()
... # doctest: +NORMALIZE_WHITESPACE
foo<x:int64> [i=0:2:0:1000000]
  name class   type nullable start end overlap    chunk
0    x  attr  int64     True
1    i   dim  int64              0   2       0  1000000

>>> db.iquery('remove(foo)')

>>> dir(db.arrays)
[]

Arrays specified explicitly are not checked:

>>> print(db.arrays.foo)
foo
>>> print(db.arrays.bar)
bar

In IPython, we can use <TAB> for auto-completion of array names,
array dimensions, and array attributes::

    In [1]: db.arrays.<TAB>
    In [1]: db.arrays.foo
    In [2]: db.arrays.foo.<TAB>
    In [2]: db.arrays.foo.x


SciDB Operators
===============

At connection time, the library downloads the list of available SciDB
operators and macros and makes them available through the ``DB`` class
instance:

>>> dir(db)
... # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS +ALLOW_UNICODE
[u'add_attributes',
 ...
 u'xgrid']

>>> db.apply
... # doctest: +NORMALIZE_WHITESPACE
Operator(db=DB('http://localhost:8080',
               None,
               None,
               None,
               False,
               None,
               False,
               256,
               False),
         name='apply',
         args=[])

>>> print(db.apply)
apply()

>>> db.missing
Traceback (most recent call last):
    ...
AttributeError: 'DB' object has no attribute 'missing'

In IPython, we can use <TAB> for auto-completion of operator names::

    In [1]: db.<TAB>
    In [1]: db.apply

The operators can be execute immediately or can be lazy and executed
at a later time. Operators that return arrays are lazy operators (e.g.,
``apply``, ``scan``, etc.). Operators which do not return arrays
execute immediately (e.g., ``create_array``, ``remove``, etc.).

>>> db.create_array('foo', '<x:int64>[i]')
>>> dir(db.arrays)
... # doctest: +ALLOW_UNICODE
[u'foo']

>>> db.remove(db.arrays.foo)
>>> dir(db.arrays)
[]

The list of available operators is re-loaded automatically when
a ``load_library`` query is issued:

>>> db.load_library('limit')
... # doctest: +SKIP
>>> 'limit' in dir(db)
... # doctest: +SKIP
True

A similar functionality is **not** implemented for ``unload_library``
operator. The ``unload_library`` operator requires a SciDB restart,
which makes re-loading the list of operators not
practical. Nevertheless, one can trigger the re-loading manually after
SciDB restart without creating a new ``DB`` instance:

>>> db.iquery("unload_library('limit')")
... # doctest: +SKIP

After SciDB restart:

>>> db.load_ops()
>>> 'limit' in dir(db)
... # doctest: +SKIP
False

The ``cross_join`` operator in SciDB supports aliasing for the array
arguments, e.g., ``cross_join(left_array as left_alias,...``. Aliasing
is possible in SciDB-Py using the ``%`` operator:

>>> db.iquery('store(build(<x:int64>[i=0:1], i), foo)')
>>> db.cross_join(db.arrays.foo % 'f1',
...               db.arrays.foo % 'f2',
...               'f1.i', 'f2.i')[:]
   i    x  x_1
0  0  0.0  0.0
1  1  1.0  1.0

>>> db.remove(db.arrays.foo)

To retrieve the schema of a query result, the ``schema`` utility
function can be used:

>>> print(db.build('<x:int64>[i=0:2]', 'i').schema())
build<x:int64> [i=0:2:0:1000000]

>>> db.build('<x:int64>[i=0:2]', 'i').schema().pprint()
... # doctest: +NORMALIZE_WHITESPACE
build<x:int64> [i=0:2:0:1000000]
  name class   type nullable start end overlap    chunk
0    x  attr  int64     True
1    i   dim  int64              0   2       0  1000000



Download Data from SciDB
------------------------

>>> db.build('<x:int8 not null>[i=0:2]', 'i + 10')[:]
   i   x
0  0  10
1  1  11
2  2  12

>>> db.build('<x:int8 not null>[i=0:2]', 'i + 10').fetch(as_dataframe=False)
... # doctest: +NORMALIZE_WHITESPACE
array([(0, 10), (1, 11), (2, 12)],
      dtype=[('i', '<i8'), ('x', 'i1')])

>>> db.build('<x:int8 not null>[i=0:2]', 'i + 10').fetch(
...     atts_only=True)
    x
0  10
1  11
2  12

>>> db.build('<x:int8 not null>[i=0:2]', 'i + 10').apply('y', 'x - 5')[:]
   i   x  y
0  0  10  5
1  1  11  6
2  2  12  7

>>> db.build('<x:int8 not null>[i=0:2]', 'i + 10').store('foo')
... # doctest: +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'foo')

>>> db.scan(db.arrays.foo)[:]
   i   x
0  0  10
1  1  11
2  2  12

>>> db.apply(db.arrays.foo, 'y', db.arrays.foo.x + 1)[:]
   i   x   y
0  0  10  11
1  1  11  12
2  2  12  13

>>> db.remove(db.arrays.foo)


Upload Data to SciDB
--------------------

``input`` and ``load`` operators can be used to upload data. An upload
schema can also be provided. If the resulting array or schema is not
provided, it can be generated from the upload data or upload
schema. If the upload format is not provided, it can be constructed
from the upload schema, upload data, or resulting array schema.

>>> db.input('<x:int64>[i]', upload_data=numpy.arange(3))[:]
   i    x
0  0  0.0
1  1  1.0
2  2  2.0

>>> db.input('<x:int64>[i]', upload_data=numpy.arange(3)).store(db.arrays.foo)
... # doctest: +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'foo')

>>> db.load(db.arrays.foo, upload_data=numpy.arange(3))
... # doctest: +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'foo')

>>> db.input('<x:int64>[j]', upload_data=numpy.arange(3, 6)
...  ).apply('i', 'j + 3'
...  ).redimension(db.arrays.foo
...  ).insert(db.arrays.foo)

>>> db.arrays.foo[:]
   i    x
0  0  0.0
1  1  1.0
2  2  2.0
3  3  3.0
4  4  4.0
5  5  5.0

>>> db.input('<i:int64 not null, x:int64>[j]',
...          upload_data=db.arrays.foo.fetch(as_dataframe=False)
...  ).redimension(db.arrays.foo
...  ).store('bar')
... # doctest: +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'bar')

>>> numpy.all(db.arrays.bar.fetch(as_dataframe=False)
...           == db.arrays.foo.fetch(as_dataframe=False))
True

>>> buf = numpy.array([bytes([10, 20, 30])], dtype='object')

>>> db.input('<b:binary not null>[i]', upload_data=buf).store('taz')
... # doctest: +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'taz')

>>> db.load('taz',
...         upload_data=buf,
...         upload_schema=Schema.fromstring('<b:binary not null>[i]'))
... # doctest: +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'taz')

For files already available on the server the ``input`` or ``load``
operators can be invoked with the full set of arguments supported by
SciDB. Arguments that need to be quoted in SciDB need to be
double-quoted in SciDB-Py. For example:

>>> db.load('foo', "'/data.csv'", 0, "'CSV'")
... # doctest: +SKIP

>>> for ar in ['foo', 'bar', 'taz']: db.remove(ar)

The ``store`` function accepts a ``temp`` argument as well. If the
``temp`` argument is set to ``True``, a temporary array is created.

>>> ar = db.build('<x:int64>[i=0:2]', 'i').store('foo', temp=True)
>>> db.list()[['name', 'temporary']]
  name  temporary
0  foo       True
>>> db.remove(ar)

If an array name is not specified for the ``store`` operator, an array
name is generated. Arrays with generated names are removed when the
returned Array object is garbage collected. This behavior can be
changed by specifying the ``gc=False`` argument to the store operator.

>>> ar = db.input(upload_data=numpy.arange(3)).store()
>>> ar
... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
Array(DB('http://localhost:8080',
         None,
         None,
         None,
         False,
         None,
         False,
         256,
         False),
      'py_...')
>>> del ar


The iquery Function
===================

Use the :meth:`DB.iquery()<scidbpy.db.DB.iquery>` function to execute
literal queries against SciDB:

>>> db.iquery('store(build(<x:int64>[i=0:2], i), foo)')


Download Data from SciDB
------------------------

The ``iquery`` function can be used to download data from SciDB by
specifying the ``fetch=True`` argument:

>>> db.iquery('scan(foo)', fetch=True)
   i    x
0  0  0.0
1  1  1.0
2  2  2.0

To avoid downloading the dimension information and only download the
attributes, use the ``atts_only=True`` argument:

>>> db.iquery('scan(foo)', fetch=True, atts_only=True)
     x
0  0.0
1  1.0
2  2.0

>>> db.iquery('remove(foo)')


Download operator output directly:

>>> db.iquery('build(<x:int64 not null>[i=0:2], i)',
...           fetch=True)
   i  x
0  0  0
1  1  1
2  2  2

>>> db.iquery('build(<x:int64 not null>[i=0:2], i)',
...           fetch=True,
...           atts_only=True)
   x
0  0
1  1
2  2


If dimension names collide with attribute names, unique dimension
names are created:

>>> db.iquery('apply(build(<x:int64 not null>[i=0:2], i), i, i)', fetch=True)
   i_1  x  i
0    0  0  0
1    1  1  1
2    2  2  2


If schema is known, it can be provided to ``iquery`` using the
``schema`` argument. This speeds up the execution as ``iquery`` does
not need to issue a ``show()`` query first in order to determine the
schema:

>>> from scidbpy import Schema
>>> iquery(db,
...        'build(<x:int64 not null>[i=0:2], i)',
...        fetch=True,
...        schema=Schema(None,
...                      (Attribute('x', 'int64', not_null=True),),
...                      (Dimension('i', 0, 2),)))
   i  x
0  0  0
1  1  1
2  2  2

>>> iquery(db,
...        'build(<x:int64 not null>[i=0:2], i)',
...        fetch=True,
...        atts_only=True,
...        schema=Schema.fromstring('<x:int64 not null>[i=0:2]'))
... # doctest: +NORMALIZE_WHITESPACE
   x
0  0
1  1
2  2


Attributes with null-able types are promoted as per Pandas `promotion
scheme <http://pandas.pydata.org/pandas-docs/stable/gotchas.html
#na-type-promotions>`_ During such promotions, precision loss might
occur. The user is notified about this via a ``UserWarning``. If
desired, such warnings can be disabled as follows:

>>> import warnings
>>> warnings.filterwarnings('ignore', category = UserWarning)

Type promotions can be avoided altogether, by specifying
``dataframe_promo = False`` in the ``iquery`` arguments. In this case,
object records will be used instead of atomic values:

>>> iquery(db,
...        'build(<x:int64>[i=0:2], i)',
...        fetch=True,
...        atts_only=True,
...        as_dataframe=True,
...        dataframe_promo=False)
... # doctest: +NORMALIZE_WHITESPACE
   x
0  (255, 0)
1  (255, 1)
2  (255, 2)


Download as NumPy Array:

>>> iquery(db,
...        'build(<x:int64>[i=0:2], i)',
...        fetch=True,
...        as_dataframe=False)
... # doctest: +NORMALIZE_WHITESPACE
array([(0, (255, 0)), (1, (255, 1)), (2, (255, 2))],
      dtype=[('i', '<i8'), ('x', [('null', 'u1'), ('val', '<i8')])])

>>> iquery(db,
...        'build(<x:int64>[i=0:2], i)',
...        fetch=True,
...        atts_only=True,
...        as_dataframe=False)
... # doctest: +NORMALIZE_WHITESPACE
array([((255, 0),), ((255, 1),), ((255, 2),)],
      dtype=[('x', [('null', 'u1'), ('val', '<i8')])])


If the `accelerated_io_tools
<https://github.com/Paradigm4/accelerated_io_tools>`_ SciDB plugin is
installed and enabled in `Shim <https://github.com/Paradigm4/shim>`_,
SciDB arrays can be downloaded using the Apache Arrow library:

>>> db.iquery('scan(foo)', fetch=True, use_arrow=True)
... # doctest: +SKIP
   i    x
0  0  0.0
1  1  1.0
2  2  2.0


By default, Apache Arrow is not used. If desired, ``use_arrow`` can be
set to ``True`` at connection time (it is ``False`` by default). Once
set at connection time, this value is used for any subsequent
``iquery`` calls if not overwritten:

>>> db_arrow = connect(use_arrow=True)
>>> db_arrow.iquery('scan(foo)', fetch=True)
... # doctest: +SKIP
   i    x
0  0  0.0
1  1  1.0
2  2  2.0


Upload Data to SciDB
--------------------

Data can be uploaded using the ``iquery`` function by providing an
``upload_data`` argument. A file name placeholder needs to be provided
as part of the SciDB query string. The upload array schema and data
format can be provided explicitly or as placeholders in the query
string. The placeholders are replaced with the explicit values by the
``iquery`` function, before the query is sent to SciDB.

The SciDB query placeholders are:

* ``'{fn}'``: **mandatory** placeholder which is replaced with the
  file name of the server file where the uploaded data is stored. It
  has to be *quoted* with single quotes in the query string.

* ``{sch}``: *optional* placeholder which is replaced with the upload
  array schema. It does *not* need to be quoted.

* ``'{fmt}'``: *optional* placeholder which is replaced with the
  upload array format.  It has to be *quoted* with single quotes in
  the query string.

See examples in the following subsections.


Upload NumPy Arrays
^^^^^^^^^^^^^^^^^^^

Provide a SciDB ``input``, ``store``, ``insert``, or ``load`` query
and a NumPy array. If the schema or format are provided as
placeholders, the upload data *dtype* or upload schema is used to
populate these placeholders.

>>> db.iquery("store(input(<x:int64>[i], '{fn}', 0, '{fmt}'), foo)",
...           upload_data=numpy.arange(3))

>>> db.arrays.foo[:]
   i    x
0  0  0.0
1  1  1.0
2  2  2.0

>>> db.iquery("insert(input({sch}, '{fn}', 0, '(int64)'), foo)",
...           upload_data=numpy.arange(3))

Optionally, a ``Schema`` object can be used to specify the upload
schema using the ``upload_schema`` argument:

>>> db.iquery("load(foo, '{fn}', 0, '{fmt}')",
...           upload_data=numpy.arange(3),
...           upload_schema=Schema.fromstring('<x:int64 not null>[i]'))


Upload Binary Data
^^^^^^^^^^^^^^^^^^

Provide a SciDB ``input``, ``store``, ``insert``, or ``load`` query
and binary data. The schema of the upload data needs to be provided
either explicitly in the query string or using the ``upload_schema``
argument. If the schema is not provides using the ``upload_schema``
argument, the format needs to be provided explicitly in the query
string:

>>> db.iquery("store(input({sch}, '{fn}', 0, '{fmt}'), foo)",
...           upload_data=numpy.arange(3).tobytes(),
...           upload_schema=Schema.fromstring('<x:int64 not null>[i]'))

>>> db.iquery("insert(input(foo, '{fn}', 0, '(int64)'), foo)",
...           upload_data=numpy.arange(3).tobytes())

>>> db.iquery("load(foo, '{fn}', 0, '(int64)')",
...           upload_data=numpy.arange(3).tobytes())


Upload Data Files
^^^^^^^^^^^^^^^^^

A binary or text file-like object can be used to specify the upload
data. The content of the file has to be in one of the `supported SciDB
formats
<https://paradigm4.atlassian.net/wiki/spaces/ESD169/pages/50856232/input>`_. A
matching format specification has to be provided as well:

>>> with open('array.bin', 'wb') as file:
...     n = file.write(numpy.arange(3).tobytes())

>>> db.iquery("load(foo, '{fn}', 0, '(int64)')",
...           upload_data=open('array.bin', 'rb'))

>>> with open('array.csv', 'w') as file:
...     n = file.write('1\\n2\\n3\\n')

>>> db.iquery("load(foo, '{fn}', 0, 'CSV')",
...           upload_data=open('array.csv', 'r'))

>>> import os
>>> os.remove('array.bin')
>>> os.remove('array.csv')
>>> db.remove(db.arrays.foo)

Please note that the data file is not read into the SciDB-Py
library. The data file object is passed directly to the ``requests``
library which handles the HTTP communication with *Shim*.


Joins
=====

SciDB provides a number of join operators, including ``join``,
``cross_join``, etc. As with any other operators, these operators can
be used as literals in the ``DB.iquery`` function or as functions of
the ``DB`` object. Here are some join examples exposing various
features of the library:

>>> foo = db.build('<val:double>[i=0:2; j=0:2]', 'i * 3 + j').store('foo')

>>> db.join(foo,
...         db.build('<val:double>[i=0:2; j=0:5]', '0'))[:]
   i  j  val  val_1
0  0  0  0.0    0.0
1  0  1  1.0    0.0
2  0  2  2.0    0.0
3  1  0  3.0    0.0
4  1  1  4.0    0.0
5  1  2  5.0    0.0
6  2  0  6.0    0.0
7  2  1  7.0    0.0
8  2  2  8.0    0.0

>>> db.build('<val:double>[i=0:2; j=0:5]', '0'
...  ).join(db.arrays.foo)[:]
   i  j  val  val_1
0  0  0  0.0    0.0
1  0  1  0.0    1.0
2  0  2  0.0    2.0
3  1  0  0.0    3.0
4  1  1  0.0    4.0
5  1  2  0.0    5.0
6  2  0  0.0    6.0
7  2  1  0.0    7.0
8  2  2  0.0    8.0

>>> db.cross_join(foo,
...               db.build('<val:double>[k=0:5]', 'k + 100'),
...               foo.j, 'k')[:]
   i  j  val  val_1
0  0  0  0.0  100.0
1  0  1  1.0  101.0
2  0  2  2.0  102.0
3  1  0  3.0  100.0
4  1  1  4.0  101.0
5  1  2  5.0  102.0
6  2  0  6.0  100.0
7  2  1  7.0  101.0
8  2  2  8.0  102.0

>>> bar = db.build('<val:double>[j=0:5]', 'j + 100').store()

>>> db.cross_join(db.arrays.foo % 'left',
...               bar % 'right',
...               'left.j', 'right.j')[:]
   i  j  val  val_1
0  0  0  0.0  100.0
1  0  1  1.0  101.0
2  0  2  2.0  102.0
3  1  0  3.0  100.0
4  1  1  4.0  101.0
5  1  2  5.0  102.0
6  2  0  6.0  100.0
7  2  1  7.0  101.0
8  2  2  8.0  102.0

>>> db.remove(foo)
>>> db.remove(bar)


SciDB Enterprise Edition Features
=================================

SciDB Enterprise Edition features can be used directly as any other
operators. One special case is the ``set_namespace`` operator. The
operator alters the ``DB`` object on which it is called. The effect
persists until the next call to ``set_namespace``. The operator can be
called directly (i.g., ``db.set_namespace``) or through the ``iquery``
function. No immediate query is executed in SciDB, but the new
namespace will take effect for any subsequent SciDB queries:

>>> print(db)
scidb_url         = http://localhost:8080
scidb_auth        = None
http_auth         = None
verify            = None
admin             = False
namespace         = None
use_arrow         = False
result_size_limit = 256
no_ops            = False

Notice the ``namespace`` field of the ``DB`` instance.

>>> db.set_namespace('private')
... # doctest: +SKIP
>>> print(db)
... # doctest: +SKIP
scidb_url         = http://localhost:8080
scidb_auth        = None
http_auth         = None
verify            = None
admin             = False
namespace         = private
use_arrow         = False
result_size_limit = 256
no_ops            = False
>>> db.show_namespace()[0]['name']['val']
... # doctest: +SKIP
'private'

>>> db.iquery("set_namespace('public')")
>>> print(db)
scidb_url         = http://localhost:8080
scidb_auth        = None
http_auth         = None
verify            = None
admin             = False
namespace         = public
use_arrow         = False
result_size_limit = 256
no_ops            = False
>>> db.show_namespace()[0]['name']['val']
... # doctest: +SKIP
'public'

For convenience, an initial namespace can be provided at connection
time:

>>> db_ssl = connect('https://localhost:8083',
...                  verify=False,
...                  namespace='public')
... # doctest: +SKIP
>>> print(db_ssl)
... # doctest: +SKIP
scidb_url         = https://localhost:8083
scidb_auth        = None
http_auth         = None
verify            = False
admin             = Flase
namespace         = public
use_arrow         = False
result_size_limit = 256
no_ops            = False

"""

from .db import connect, iquery, Array
from .schema import Attribute, Dimension, Schema

__version__ = '19.3.3'
