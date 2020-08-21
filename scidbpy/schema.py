"""Attribute, Dimension, and Schema
================================

Classes for accessing SciDB data and schemas.

"""

import dateutil
import itertools
import numpy
import pandas
import re
import six
import struct
import warnings


type_map_numpy = dict(
    (k, numpy.dtype(v)) for (k, v) in
    [(t.__name__, t) for t in (
        numpy.bool,

        numpy.int8,
        numpy.int16,
        numpy.int32,
        numpy.int64,

        numpy.uint8,
        numpy.uint16,
        numpy.uint32,
        numpy.uint64,
    )] + [
        ('char', 'S1'),
        ('double', numpy.float64),
        ('float', numpy.float32),
        ('string', numpy.object),
        ('binary', numpy.object),
        ('datetime', 'datetime64[s]'),
        ('datetimetz', [('time', 'datetime64[s]'),
                        ('tz', 'timedelta64[s]')]),
    ])

type_map_inv_numpy = {v: k
                      for k, v in six.iteritems(type_map_numpy)
                      if v != numpy.dtype(numpy.object)}
type_map_inv_numpy.update(dict(
    (numpy.dtype(k), v) for (k, v) in
    [
        (numpy.str_, 'string'),
        (numpy.string_, 'string'),
        (numpy.datetime64, 'datetime'),
        (numpy.timedelta64, 'datetimetz'),
    ]))

type_map_struct = {
    'bool': '?',

    'char': 'c',

    'int8': 'b',
    'int16': '<h',
    'int32': '<i',
    'int64': '<q',

    'float': '<f',
    'double': '<d',

    'datetime': '<q',
    'datetimetz': '<qq',
    }

# Add uint types
for key in list(type_map_struct.keys()):
    if key.startswith('int'):
        type_map_struct['u' + key] = type_map_struct[key].upper()

# Add null-able type
for (key, val) in type_map_struct.items():
    if len(val) > 1:
        val_null = val[0] + 'B' + val[1]
    else:
        val_null = 'B' + val
    type_map_struct[key] = (val, val_null)

# Type promotion map for Pandas DataFrame
# http://pandas.pydata.org/pandas-docs/stable/gotchas.html#na-type-promotions
type_map_promo = dict(
    (k, numpy.dtype(v)) for (k, v) in
    [
        ('bool', numpy.object),
        ('char', numpy.object),

        ('int8', numpy.float16),
        ('int16', numpy.float32),
        ('int32', numpy.float64),
        ('int64', numpy.float64),

        ('uint8', numpy.float16),
        ('uint16', numpy.float32),
        ('uint32', numpy.float64),
        ('uint64', numpy.float64),

        ('datetime', 'datetime64[ns]'),
    ])

one_att_name = 'x'
one_dim_name = 'i'


class Attribute(object):
    """Represent SciDB array attribute

    Construct an attribute using Attribute constructor:

    >>> Attribute('foo', 'int64', not_null=True)
    ... # doctest: +NORMALIZE_WHITESPACE
    Attribute(name='foo',
              type_name='int64',
              not_null=True,
              default=None,
              compression=None)

    >>> Attribute('foo', 'int64', default=100, compression='zlib')
    ... # doctest: +NORMALIZE_WHITESPACE
    Attribute(name='foo',
              type_name='int64',
              not_null=False,
              default=100,
              compression='zlib')


    Construct an attribute from a string:

    >>> Attribute.fromstring('foo:int64')
    ... # doctest: +NORMALIZE_WHITESPACE
    Attribute(name='foo',
              type_name='int64',
              not_null=False,
              default=None,
              compression=None)

    >>> Attribute.fromstring(
    ...     "taz : string NOT null DEFAULT '' compression 'bzlib'")
    ... # doctest: +NORMALIZE_WHITESPACE
    Attribute(name='taz',
              type_name='string',
              not_null=True,
              default="''",
              compression='bzlib')
    """

    _regex = re.compile('''
        \\s*
        (?P<name>      \\w+ )  \\s* : \\s*
        (?P<type_name> \\w+ )  \\s*
        (?:                   (?P<not_null>    NOT )? \\s+ NULL )? \\s*
        (?: DEFAULT     \\s+  (?P<default>     \\S+ )           )? \\s*
        (?: COMPRESSION \\s+ '(?P<compression> \\w+ )'          )? \\s*
        $''', re.VERBOSE | re.IGNORECASE)
    # length dtype for variable-size SciDB types
    _length_dtype = numpy.dtype(numpy.uint32)
    _length_fmt = '<I'

    def __init__(self,
                 name,
                 type_name,
                 not_null=False,
                 default=None,
                 compression=None):
        self.__name = name
        self.type_name = type_name
        self.not_null = bool(not_null)
        self.default = default
        self.compression = compression

        self.fmt_scidb = '{}{}'.format(self.type_name,
                                       '' if self.not_null else ' null')
        self.fmt_struct = type_map_struct.get(self.type_name, None)

        self._set_dtype()

    def __iter__(self):
        return (i for i in (
            self.name,
            self.type_name,
            self.not_null,
            self.default,
            self.compression))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __repr__(self):
        return ('{}(' +
                'name={!r}, ' +
                'type_name={!r}, ' +
                'not_null={!r}, ' +
                'default={!r}, ' +
                'compression={!r})').format(
            type(self).__name__, *self)

    def __str__(self):
        return '{}:{}{}{}{}'.format(
            self.name,
            self.type_name,
            ' NOT NULL' if self.not_null else '',
            ' DEFAULT {}'.format(self.default) if self.default else '',
            " COMPRESSION '{}'".format(self.compression)
            if self.compression else '')

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value
        self._set_dtype()

    def _set_dtype(self):
        self.dtype_val = type_map_numpy.get(self.type_name, numpy.object)
        # >>> numpy.dtype([(u"a", int)])
        # TypeError: data type not understood
        # https://github.com/numpy/numpy/issues/2407
        # cannot use `self.name` directly, use `str(...)`
        if self.not_null:
            self.dtype = numpy.dtype([(str(self.name), self.dtype_val)])
        else:
            self.dtype = numpy.dtype([(str(self.name),
                                       [('null', numpy.uint8),
                                        ('val', self.dtype_val)])])

    def is_fixsize(self):
        return self.dtype_val != numpy.object

    def itemsize(self, buf=None, offset=0):
        if self.dtype_val != numpy.object:
            return self.dtype.itemsize

        null_size = 0 if self.not_null else 1
        value_size = numpy.frombuffer(
            buf, numpy.uint32, 1, offset + null_size)[0]
        return null_size + Attribute._length_dtype.itemsize + value_size

    def frombytes(self, buf, offset=0, size=None, promo=False):
        null_size = 0 if self.not_null else 1

        if self.dtype_val == numpy.object:
            if self.type_name == 'string':
                val = buf[offset + null_size +
                          Attribute._length_dtype.itemsize:
                          offset + size - 1].decode('utf-8')
            else:
                val = buf[offset + null_size +
                          Attribute._length_dtype.itemsize:
                          offset + size]
        else:
            val = struct.unpack(
                self.fmt_struct[0], buf[offset + null_size:offset + size])
            if len(val) == 1:
                val = val[0]

        if self.not_null:
            return val
        else:
            missing = struct.unpack('B', buf[offset:offset + null_size])[0]
            if promo:
                return val if missing == 255 else None
            else:
                return (missing, val)

    def tobytes(self, val):
        if self.dtype_val == numpy.object:
            if self.type_name == 'string':
                val_enc = val.encode('utf-8')
                buf = b''.join(
                    [struct.pack(Attribute._length_fmt, len(val_enc) + 1),
                     val_enc,
                     b'\x00'])
            elif self.type_name == 'binary':
                buf = b''.join(
                    [struct.pack(Attribute._length_fmt, len(val)), val])
            else:
                raise NotImplementedError('Convert <{}> to bytes'.format(self))
        else:
            if self.not_null:
                buf = struct.pack(self.fmt_struct[0], val)
            else:
                if isinstance(val, numpy.void):
                    # NumPy structured array
                    buf = struct.pack(self.fmt_struct[1], *val)
                else:
                    buf = struct.pack(self.fmt_struct[1], 255, val)
        return buf

    @classmethod
    def fromstring(cls, string):
        try:
            return cls(**Attribute._regex.match(string).groupdict())
        except AttributeError:
            raise Exception('Failed to parse attribute: {}'.format(string))

    @classmethod
    def fromdtype(cls, dtype_descr):
        if isinstance(dtype_descr[1], str):
            # e.g. ('name', 'int64')
            dtype_val = dtype_descr[1]
            not_null = True
        else:
            # e.g. ('name', [('null': 'int8'), ('val': 'int64')]
            #      ('name', [('time', 'datetime64'), ('tz', 'timedelta64')])
            #      ('name', [('null': 'int8'),
            #                ('val' : [('time', 'datetime64'),
            #                          ('tz', 'timedelta64')])])
            if dtype_descr[1][0][0] == 'null':
                not_null = False
                dtype_val = dtype_descr[1][1][1]
            else:
                not_null = True
                dtype_val = dtype_descr[1]

        dtype_val = numpy.dtype(dtype_val)
        if dtype_val in type_map_inv_numpy.keys():
            type_name = type_map_inv_numpy[dtype_val]
        else:
            # if dtype_val not found in map, try the dtype_val.type
            # (without the length)
            ty = numpy.dtype(dtype_val.type)
            # e.g. '<U3' --type--> '<U' --map--> numpy.str_
            if ty in type_map_inv_numpy.keys():
                type_name = type_map_inv_numpy[ty]
            else:
                raise Exception(
                    'No SciDB type mapping for NumPy type {}'.format(
                        dtype_val))

        return cls(name=dtype_descr[0] if dtype_descr[0] else one_att_name,
                   type_name=type_name,
                   not_null=not_null)


class Dimension(object):
    """Represent SciDB array dimension

    Construct a dimension using the Dimension constructor:

    >>> Dimension('foo')
    ... # doctest: +NORMALIZE_WHITESPACE
    Dimension(name='foo',
              low_value=None,
              high_value=None,
              chunk_overlap=None,
              chunk_length=None)

    >>> Dimension('foo', -100, '10', '?', '1000')
    ... # doctest: +NORMALIZE_WHITESPACE
    Dimension(name='foo',
              low_value=-100,
              high_value=10,
              chunk_overlap='?',
              chunk_length=1000)


    Construct a dimension from a string:

    >>> Dimension.fromstring('foo')
    ... # doctest: +NORMALIZE_WHITESPACE
    Dimension(name='foo',
              low_value=None,
              high_value=None,
              chunk_overlap=None,
              chunk_length=None)

    >>> Dimension.fromstring('foo=-100:*:?:10')
    ... # doctest: +NORMALIZE_WHITESPACE
    Dimension(name='foo',
              low_value=-100,
              high_value='*',
              chunk_overlap='?',
              chunk_length=10)
    """

    _regex = re.compile('''
        \\s*
        (?P<name> \\w+ ) \\s*
        (?: = \\s* (?P<low_value>  [^:\\s]+ ) \\s*
                   : \\s*
                   (?P<high_value> [^:\\s]+ ) \\s*
                   (?: : \\s* (?P<chunk_overlap> [^:\\s]+ ) \\s*
                              (?: : \\s* (?P<chunk_length> [^:\\s]+ ) )?
                   )?
        )?
        \\s* $''', re.VERBOSE)

    def __init__(self,
                 name,
                 low_value=None,
                 high_value=None,
                 chunk_overlap=None,
                 chunk_length=None):
        self.name = name

        try:
            self.low_value = int(low_value)
        except (TypeError, ValueError):
            self.low_value = low_value

        try:
            self.high_value = int(high_value)
        except (TypeError, ValueError):
            self.high_value = high_value

        try:
            self.chunk_overlap = int(chunk_overlap)
        except (TypeError, ValueError):
            self.chunk_overlap = chunk_overlap

        try:
            self.chunk_length = int(chunk_length)
        except (TypeError, ValueError):
            self.chunk_length = chunk_length

    def __iter__(self):
        return (i for i in (
            self.name,
            self.low_value,
            self.high_value,
            self.chunk_overlap,
            self.chunk_length))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __repr__(self):
        return ('{}(' +
                'name={!r}, ' +
                'low_value={!r}, ' +
                'high_value={!r}, ' +
                'chunk_overlap={!r}, ' +
                'chunk_length={!r})').format(
            type(self).__name__, *self)

    def __str__(self):
        out = self.name
        if self.low_value is not None:
            out += '={}:{}'.format(self.low_value, self.high_value)
            if self.chunk_overlap is not None:
                out += ':{}'.format(self.chunk_overlap)
                if self.chunk_length is not None:
                    out += ':{}'.format(self.chunk_length)
        return out

    @classmethod
    def fromstring(cls, string):
        try:
            return cls(**Dimension._regex.match(string).groupdict())
        except AttributeError:
            raise Exception('Failed to parse dimension: {}'.format(string))


class Schema(object):
    """Represent SciDB array schema

    Construct a schema using Schema, Attribute, and Dimension
    constructors:

    >>> Schema('foo', (Attribute('x', 'int64'),), (Dimension('i', 0, 10),))
    ... # doctest: +NORMALIZE_WHITESPACE
    Schema(name='foo',
           atts=(Attribute(name='x',
                           type_name='int64',
                           not_null=False,
                           default=None,
                           compression=None),),
           dims=(Dimension(name='i',
                           low_value=0,
                           high_value=10,
                           chunk_overlap=None,
                           chunk_length=None),))


    Construct a schema using Schema constructor and fromstring methods
    of Attribute and Dimension:

    >>> Schema('foo',
    ...        (Attribute.fromstring('x:int64'),),
    ...        (Dimension.fromstring('i=0:10'),))
    ... # doctest: +NORMALIZE_WHITESPACE
    Schema(name='foo',
           atts=(Attribute(name='x',
                           type_name='int64',
                           not_null=False,
                           default=None,
                           compression=None),),
           dims=(Dimension(name='i',
                           low_value=0,
                           high_value=10,
                           chunk_overlap=None,
                           chunk_length=None),))


    Construct a schema from a string:

    >>> Schema.fromstring(
    ...     'foo@1<x:int64 not null, y:double>[i=0:*; j=-100:0:0:10]')
    ... # doctest: +NORMALIZE_WHITESPACE
    Schema(name='foo@1',
           atts=(Attribute(name='x',
                           type_name='int64',
                           not_null=True,
                           default=None,
                           compression=None),
                 Attribute(name='y',
                           type_name='double',
                           not_null=False,
                           default=None,
                           compression=None)),
           dims=(Dimension(name='i',
                           low_value=0,
                           high_value='*',
                           chunk_overlap=None,
                           chunk_length=None),
                 Dimension(name='j',
                           low_value=-100,
                           high_value=0,
                           chunk_overlap=0,
                           chunk_length=10)))


    Print a schema constructed from a string:

    >>> print(Schema.fromstring('<x:int64,y:float> [i=0:2:0:1000000; j=0:*]'))
    ... # doctest: +NORMALIZE_WHITESPACE
    <x:int64,y:float> [i=0:2:0:1000000; j=0:*]


    Format Schema object to only print the schema part without the
    array name:

    >>> '{:h}'.format(Schema.fromstring('foo<x:int64>[i]'))
    '<x:int64> [i]'
    """

    _regex_name = re.compile(
        '\\s* (?: not \\s+ empty \\s+ )? (?P<name> [\\w@]+ )?', re.VERBOSE)

    _regex_atts = re.compile(
        '\\s*  < ( [^,>]+  \\s* (?: , \\s* [^,>]+  \\s* )* )  >', re.VERBOSE)

    _regex_dims = re.compile(
        '\\s* \\[ ( [^;\\]]+ \\s* (?: ; \\s* [^;\\]]+ \\s* )* ) \\] \\s*',
        re.VERBOSE)

    def __init__(self, name=None, atts=(), dims=()):
        self.name = name
        self.atts = tuple(atts)
        self.dims = tuple(dims)

        # Set lazy
        self.__atts_dtype = None
        self.__atts_fmt_scidb = None

    def __iter__(self):
        return (i for i in (self.name, ) + self.atts + self.dims)

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __repr__(self):
        return '{}(name={!r}, atts={!r}, dims={!r})'.format(
            type(self).__name__, self.name, self.atts, self.dims)

    def __str__(self):
        return self._render()

    def __format__(self, fmt_spec=''):
        return self._render(no_name='h' in fmt_spec)

    def _render(self, no_name=False):
        return '{}<{}> [{}]'.format(
            self.name if not no_name and self.name else '',
            ','.join(str(a) for a in self.atts),
            '; '.join(str(d) for d in self.dims))

    def _promo_warning(self):
        cnt = sum(not a.not_null for a in self.atts)
        if cnt:
            warnings.warn(
                ('{} type(s) promoted for null support.' +
                 ' Precision loss may occur').format(cnt),
                stacklevel=2)

    @property
    def atts_dtype(self):
        if self.__atts_dtype is None:
            self.__atts_dtype = numpy.dtype(list(itertools.chain.from_iterable(
                a.dtype.descr for a in self.atts)))
        return self.__atts_dtype

    @property
    def atts_fmt_scidb(self):
        if self.__atts_fmt_scidb is None:
            self.__atts_fmt_scidb = '({})'.format(
                ', '.join(a.fmt_scidb for a in self.atts))
        return self.__atts_fmt_scidb

    def pprint(self):
        print(self)
        info = numpy.empty(
            (len(self.atts) + len(self.dims),),
            dtype=[('name', numpy.object),
                   ('class', numpy.object),
                   ('type', numpy.object),
                   ('nullable', numpy.object),
                   ('start', numpy.object),
                   ('end', numpy.object),
                   ('overlap', numpy.object),
                   ('chunk', numpy.object)])
        pos = 0
        for a in self.atts:
            info.put((pos,),
                     (a.name,
                      'attr',
                      a.type_name,
                      not a.not_null,
                      '',
                      '',
                      '',
                      ''))
            pos += 1
        for d in self.dims:
            info.put((pos,),
                     (d.name,
                      'dim',
                      'int64',
                      '',
                      d.low_value,
                      d.high_value,
                      d.chunk_overlap,
                      d.chunk_length))
            pos += 1
        print(pandas.DataFrame.from_records(info))

    def is_fixsize(self):
        return all(a.is_fixsize() for a in self.atts)

    def make_unique(self):
        """Make dimension and attribute names unique within the schema. Return
        ``True`` if any dimension or attribute was renamed.

        >>> s = Schema(None, (Attribute('i', 'bool'),), (Dimension('i'),))
        >>> print(s)
        <i:bool> [i]
        >>> s.make_unique()
        True
        >>> print(s)
        <i:bool> [i_1]

        >>> s = Schema.fromstring('<i:bool, i:int64>[i;i_1;i]')
        >>> s.make_unique()
        True
        >>> print(s)
        <i:bool,i_2:int64> [i_3; i_1; i_4]

        """
        all_before = set(itertools.chain((a.name for a in self.atts),
                                         (d.name for d in self.dims)))

        # Check if overall duplicates are present
        if len(all_before) < len(self.atts) + len(self.dims):

            all_after = set()

            # Process attributes
            for a in self.atts:
                # Start renaming after the first copy. First copy
                # will not be in all_after. From second copy
                # on-wards, a copy will be in all_after.
                if a.name in all_after:
                    new_name_tmpl = a.name + '_{}'
                    count = 1
                    new_name = new_name_tmpl.format(count)
                    while (new_name in all_before or
                           new_name in all_after):
                        count += 1
                        new_name = new_name_tmpl.format(count)
                    a.name = new_name
                all_after.add(a.name)

            # Process dimensions
            for d in self.dims:
                if d.name in all_after:
                    new_name_tmpl = d.name + '_{}'
                    count = 1
                    new_name = new_name_tmpl.format(count)
                    while (new_name in all_before or
                           new_name in all_after):
                        count += 1
                        new_name = new_name_tmpl.format(count)
                    d.name = new_name
                all_after.add(d.name)

            # Reset dtype
            self.__atts_dtype = None

            return True
        else:
            return False

    def make_dims_atts(self):
        """Make attributes from dimensions and pre-append them to the
        attributes list.

        >>> s = Schema(None, (Attribute('x', 'bool'),), (Dimension('i'),))
        >>> print(s)
        <x:bool> [i]
        >>> s.make_dims_atts()
        >>> print(s)
        <i:int64 NOT NULL,x:bool> [i]

        >>> s = Schema.fromstring('<x:bool>[i;j]')
        >>> s.make_dims_atts()
        >>> print(s)
        <i:int64 NOT NULL,j:int64 NOT NULL,x:bool> [i; j]

        """
        self.atts = tuple(itertools.chain(
            (Attribute(d.name, 'int64', not_null=True) for d in self.dims),
            self.atts))

        # Reset
        self.__atts_dtype = None
        self.__atts_fmt_scidb = None

    def get_promo_atts_dtype(self):
        self._promo_warning()
        return numpy.dtype(
            [a.dtype.descr[0] if a.not_null else
             (a.dtype.names[0],
              type_map_promo.get(
                  a.type_name, type_map_numpy.get(a.type_name, numpy.object)))
             for a in self.atts])

    def promote(self, data):
        """Promote nullable attributes in the DataFrame to types which
        support some type of null values as per Pandas `promotion
        scheme <http://pandas.pydata.org/pandas-docs/stable/gotchas.html
        #na-type-promotions>`_

        """
        self._promo_warning()
        for a in self.atts:
            if not a.not_null:
                if a.type_name == 'datetimetz':
                    # Special case to promote SciDB datetimetz to Pandas
                    type_name = 'datetime'
                    data[a.name] = pandas.Series(
                        data=[pandas.Timestamp(attr[1][0],
                                               # Cnvert UTC offset to timezone
                                               tz=dateutil.tz.tzoffset(
                                                   None, offset=attr[1][1]))
                              if attr[0] == 255 else numpy.NAN
                              for attr in data[a.name]],
                        dtype=type_map_promo.get(
                            type_name, type_map_numpy.get(
                                type_name, numpy.object)))
                else:
                    # All other types
                    data[a.name] = pandas.Series(
                        data=[attr[1] if attr[0] == 255 else numpy.NAN
                              for attr in data[a.name]],
                        dtype=type_map_promo.get(
                            a.type_name, type_map_numpy.get(
                                a.type_name, numpy.object)))

    def frombytes(self, buf, as_dataframe=False, dataframe_promo=True):
        # Scan content and build (offset, size) metadata
        off = 0
        buf_meta = []
        while off < len(buf):
            meta = []
            for att in self.atts:
                sz = att.itemsize(buf, off)
                meta.append((off, sz))
                off += sz
            buf_meta.append(meta)

        # Create NumPy record array
        if as_dataframe and dataframe_promo:
            data = numpy.empty((len(buf_meta),),
                               dtype=self.get_promo_atts_dtype())
        else:
            data = numpy.empty((len(buf_meta),), dtype=self.atts_dtype)

        # Extract values using (offset, size) metadata
        # Populate NumPy record array
        pos = 0
        for meta in buf_meta:
            data.put((pos,),
                     tuple(att.frombytes(
                         buf,
                         off,
                         sz,
                         promo=as_dataframe and dataframe_promo)
                           for (att, (off, sz)) in zip(self.atts, meta)))
            pos += 1
        return data

    def tobytes(self, data):
        buf_lst = []
        if len(data.dtype) > 0:
            # NumPy structured array
            if len(self.atts_dtype) == 1:
                # One attribute
                atr = self.atts[0]
                for cell in data:
                    buf_lst.append(atr.tobytes(cell[0]))
            else:
                # Multiple attributes
                for cell in data:
                    for (atr, val) in zip(self.atts, cell):
                        buf_lst.append(atr.tobytes(val))
        else:
            # NumPy single-field array
            atr = self.atts[0]
            for val in data:
                buf_lst.append(atr.tobytes(val))
        return b''.join(buf_lst)

    @classmethod
    def fromstring(cls, string):
        name_match = Schema._regex_name.match(string)
        atts_match = Schema._regex_atts.match(string, name_match.end(0))
        dims_match = Schema._regex_dims.match(string, atts_match.end(0))

        name = name_match.groupdict()['name']
        return cls(
            name.strip() if name else None,
            (Attribute.fromstring(s)
             for s in atts_match.group(1).split(',')),
            (Dimension.fromstring(s)
             for s in dims_match.group(1).split(';')))

    @classmethod
    def fromdtype(cls, dtype):
        return cls(
            None,
            (Attribute.fromdtype(dt) for dt in dtype.descr),
            (Dimension(one_dim_name),))


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.REPORT_ONLY_FIRST_FAILURE)
