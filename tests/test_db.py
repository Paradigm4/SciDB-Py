import gc
import numpy
import pandas
import pytest
import random
import requests
import threading
import time

from scidbpy.db import Array, connect, iquery
from scidbpy.schema import Schema


@pytest.fixture(scope='module')
def db():
    return connect()


class TestDB:

    @pytest.mark.parametrize('query', [
        'list()',
        "list('operators')",
    ])
    def test_iquery(self, db, query):
        assert db.iquery(query) is None
        assert type(
            db.iquery(query, fetch=True, as_dataframe=False)) == numpy.ndarray

    @pytest.mark.parametrize('query_batch', [
        [('store(build(<val:double>[i=1:10,10,0], i), pytest_1)', False),
         ('versions(pytest_1)', True),
         ('remove(pytest_1)', False)],
    ])
    def test_iquery_batch(self, db, query_batch):
        for (query, fetch) in query_batch:
            if fetch:
                assert type(db.iquery(
                    query, fetch=fetch, as_dataframe=False)) == numpy.ndarray
            else:
                assert db.iquery(
                    query, fetch=fetch, as_dataframe=False) is None

    @pytest.mark.parametrize(('type_name', 'schema'), [
        (type_name, schema)
        for type_name in [
                '{}int{}'.format(pre, sz)
                for pre in ('', 'u')
                for sz in (8, 16, 32, 64)
        ] + [
            'bool',
            'double',
            'float',
        ] + [
            '{}int{}'.format(u, sz)
            for u in ('', 'u') for sz in (8, 16, 32, 64)
        ]
        for schema in [
                None,
                'build<val:{}>[i=1:10,10,0]'.format(type_name),
                '<val:{}>[i=1:10,10,0]'.format(type_name),
                '<val:{}>[i=1:10]'.format(type_name),
                '<val:{}>[i]'.format(type_name),
        ]
    ])
    @pytest.mark.parametrize('atts_only', [
        True,
        False,
    ])
    def test_fetch_numpy(self, db, type_name, atts_only, schema):
        # NumPy array
        ar = iquery(
            db,
            'build(<val:{}>[i=1:10,10,0], random())'.format(type_name),
            fetch=True,
            atts_only=atts_only,
            as_dataframe=False,
            schema=schema)
        if not atts_only:
            for i in range(10):
                assert ar[i][0] == i + 1
        assert ar.shape == (10,)
        assert ar.ndim == 1

    @pytest.mark.parametrize(('type_name', 'schema'), [
        (type_name, schema)
        for type_name in [
                '{}int{}'.format(pre, sz)
                for pre in ('', 'u')
                for sz in (8, 16, 32, 64)
        ] + [
            'bool',
            'double',
            'float',
            'int8',
            'uint64',
        ]
        for schema in [
                None,
                'build<val:{}>[i=1:10,10,0]'.format(type_name),
                '<val:{}>[i=1:10,10,0]'.format(type_name),
                '<val:{}>[i=1:10]'.format(type_name),
                '<val:{}>[i]'.format(type_name),
        ]
    ])
    def test_fetch_dataframe(self, db, type_name, schema):
        # Pandas DataFrame
        ar = iquery(
            db,
            'build(<val:{}>[i=1:10,10,0], random())'.format(type_name),
            fetch=True,
            schema=schema)
        assert ar.shape == (10, 2)
        assert ar.ndim == 2

    @pytest.mark.parametrize(('type_name', 'schema'), [
        (type_name, schema)
        for type_name in [
                '{}int{}'.format(pre, sz)
                for pre in ('', 'u')
                for sz in (8, 16, 32, 64)
        ] + [
            'bool',
            'double',
            'float',
            'int8',
            'uint64',
        ]
        for schema in [
                None,
                'build<val:{}>[i=1:10,10,0]'.format(type_name),
                '<val:{}>[i=1:10,10,0]'.format(type_name),
                '<val:{}>[i=1:10]'.format(type_name),
                '<val:{}>[i]'.format(type_name),
        ]
    ])
    def test_fetch_dataframe_atts(self, db, type_name, schema):
        # Pandas DataFrame
        ar = iquery(
            db,
            'build(<val:{}>[i=1:10,10,0], random())'.format(type_name),
            fetch=True,
            atts_only=True,
            schema=schema)
        assert ar.shape == (10, 1)
        assert ar.ndim == 2

    def test_flood(self):
        for i in range(100):
            db = connect()
            del db
            gc.collect()

    def test_result_size_limit(self):
        db = connect()
        assert db.result_size_limit == 256
        db.build('<x:int64>[i=1:1000; j=1:1000]', 'i')[:]

        db.result_size_limit = 1
        assert db.result_size_limit == 1
        # with pytest.raises(requests.exceptions.HTTPError) as exc:
        #     db.build('<x:int64>[i=1:1000; j=1:1000]', 'i')[:]
        # assert 'SCIDB_LE_FILE_WRITE_ERROR' in str(exc.value)

        db = connect(result_size_limit=1)
        assert db.result_size_limit == 1
        # with pytest.raises(requests.exceptions.HTTPError) as exc:
        #     db.build('<x:int64>[i=1:1000; j=1:1000]', 'i')[:]
        # assert 'SCIDB_LE_FILE_WRITE_ERROR' in str(exc.value)


modes = ('var', 'fix')

types_atts_types = {
    'var': """b  :bool       null compression 'zlib',
              c  :char       null compression 'bzlib',
              d  :double     null,
              f  :float      null,
              i8 :int8       null,
              i16:int16      null,
              i32:int32      null,
              i64:int64      null,
              s  :string     null,
              u8 :uint8      null,
              u16:uint16     null,
              u32:uint32     null,
              u64:uint64     null""",
    'fix': """b  :bool       null compression 'zlib',
              c  :char       null compression 'bzlib',
              d  :double     null,
              f  :float      null,
              i8 :int8       null,
              i16:int16      null,
              i32:int32      null,
              i64:int64      null,
              u8 :uint8      null,
              u16:uint16     null,
              u32:uint32     null,
              u64:uint64     null"""}

types_atts = dict((mode, [at.split(':')[0].strip()
                          for at in types_atts_types[mode].split(',')])
                  for mode in modes)

types_queries = {
    'create': [
        'create array types_var_i<{}>[i=0:2]'.format(types_atts_types['var']),

        'create array types_fix_i<{}>[i=0:2]'.format(types_atts_types['fix']),

        'create array types_var<{}>[i=0:2; j=-2:0; k=0:*]'.format(
            types_atts_types['var']),

        'create array types_fix<{}>[i=0:2; j=-2:0; k=0:*]'.format(
            types_atts_types['fix']),

        """store(
             build(
               types_var_i,
               '[(true,
                  "a",
                  1.7976931348623157e+308,
                  -3.4028234663852886e+38,
                  -128,
                  -32768,
                  -2147483648,
                  -9223372036854775808,
                  "abcDEF123",
                  255,
                  65535,
                  4294967295,
                  18446744073709551615),
                 (null,
                  null,
                  null,
                  ?34,
                  ?7,
                  ?15,
                  ?31,
                  ?63,
                  null,
                  null,
                  null,
                  null,
                  null),
                 (?99,
                  ?65,
                  -inf,
                  inf,
                  null,
                  null,
                  null,
                  null,
                  ?99,
                  ?8,
                  ?16,
                  ?32,
                  ?64)]',
               true),
             types_var_i)""",

        """store(
             build(
               types_fix_i,
               '[(true,
                  "a",
                  1.7976931348623157e+308,
                  -3.4028234663852886e+38,
                  -128,
                  -32768,
                  -2147483648,
                  -9223372036854775808,
                  255,
                  65535,
                  4294967295,
                  18446744073709551615),
                 (null,
                  null,
                  null,
                  ?34,
                  ?7,
                  ?15,
                  ?31,
                  ?63,
                  null,
                  null,
                  null,
                  null),
                 (?99,
                  ?65,
                  -inf,
                  inf,
                  null,
                  null,
                  null,
                  null,
                  ?8,
                  ?16,
                  ?32,
                  ?64)]',
               true),
             types_fix_i)""",

        """store(
             filter(
               redimension(
                 cross_join(
                   cross_join(
                     types_var_i,
                     build(<x:int8 null>[j=-2:0], null)),
                   build(<y:int8 null>[k=0:2], null)),
                 types_var),
               j != 0 and k != 1),
             types_var)""",

        """store(
             filter(
               redimension(
                 cross_join(
                   cross_join(
                     types_fix_i,
                     build(<x:int8 null>[j=-2:0], null)),
                   build(<y:int8 null>[k=0:2], null)),
                 types_fix),
               j != 0 and k != 1),
             types_fix)"""],

    'clean': [
        'remove(types_var_i)',
        'remove(types_fix_i)',
        'remove(types_var)',
        'remove(types_fix)']}

types_schema = {
    'var': types_queries['create'][2][len('create array '):],
    'fix': types_queries['create'][3][len('create array '):]
}

types_array_struct = {
    'var': numpy.array(
        [(0, -2, 0,
          (255, True),
          (255, b'a'),
          (255, 1.7976931348623157e+308),
          (255, -3.4028234663852886e+38),
          (255, -128),
          (255, -32768),
          (255, -2147483648),
          (255, -9223372036854775808),
          (255, 'abcDEF123'),
          (255, 255),
          (255, 65535),
          (255, 4294967295),
          (255, 18446744073709551615)),
         (1, -2, 0,
          (0, False),
          (0, b''),
          (0, 0.0),
          (34, 0.0),
          (7, 0),
          (15, 0),
          (31, 0),
          (63, 0),
          (0, ''),
          (0, 0),
          (0, 0),
          (0, 0),
          (0, 0)),
         (2, -2, 0,
          (99, False),
          (65, b''),
          (255, -numpy.inf),
          (255, numpy.inf),
          (0, 0),
          (0, 0),
          (0, 0),
          (0, 0),
          (99, ''),
          (8, 0),
          (16, 0),
          (32, 0),
          (64, 0))],
        dtype=[('i', '<i8'), ('j', '<i8'), ('k', '<i8'),
               ('b', [('null', 'u1'), ('val', '?')]),
               ('c', [('null', 'u1'), ('val', 'S1')]),
               ('d', [('null', 'u1'), ('val', '<f8')]),
               ('f', [('null', 'u1'), ('val', '<f4')]),
               ('i8', [('null', 'u1'), ('val', 'i1')]),
               ('i16', [('null', 'u1'), ('val', '<i2')]),
               ('i32', [('null', 'u1'), ('val', '<i4')]),
               ('i64', [('null', 'u1'), ('val', '<i8')]),
               ('s', [('null', 'u1'), ('val', 'O')]),
               ('u8', [('null', 'u1'), ('val', 'u1')]),
               ('u16', [('null', 'u1'), ('val', '<u2')]),
               ('u32', [('null', 'u1'), ('val', '<u4')]),
               ('u64', [('null', 'u1'), ('val', '<u8')])]),

    'fix': numpy.array(
        [(0, -2, 0,
          (255, True),
          (255, b'a'),
          (255, 1.7976931348623157e+308),
          (255, -3.4028234663852886e+38),
          (255, -128),
          (255, -32768),
          (255, -2147483648),
          (255, -9223372036854775808),
          (255, 255),
          (255, 65535),
          (255, 4294967295),
          (255, 18446744073709551615)),
         (1, -2, 0,
          (0, False),
          (0, b''),
          (0, 0.0),
          (34, 0.0),
          (7, 0),
          (15, 0),
          (31, 0),
          (63, 0),
          (0, 0),
          (0, 0),
          (0, 0),
          (0, 0)),
         (2, -2, 0,
          (99, False),
          (65, b''),
          (255, -numpy.inf),
          (255, numpy.inf),
          (0, 0),
          (0, 0),
          (0, 0),
          (0, 0),
          (8, 0),
          (16, 0),
          (32, 0),
          (64, 0))],
        dtype=[('i', '<i8'), ('j', '<i8'), ('k', '<i8'),
               ('b', [('null', 'u1'), ('val', '?')]),
               ('c', [('null', 'u1'), ('val', 'S1')]),
               ('d', [('null', 'u1'), ('val', '<f8')]),
               ('f', [('null', 'u1'), ('val', '<f4')]),
               ('i8', [('null', 'u1'), ('val', 'i1')]),
               ('i16', [('null', 'u1'), ('val', '<i2')]),
               ('i32', [('null', 'u1'), ('val', '<i4')]),
               ('i64', [('null', 'u1'), ('val', '<i8')]),
               ('u8', [('null', 'u1'), ('val', 'u1')]),
               ('u16', [('null', 'u1'), ('val', '<u2')]),
               ('u32', [('null', 'u1'), ('val', '<u4')]),
               ('u64', [('null', 'u1'), ('val', '<u8')])]),
}

types_array_obj = dict(
    (mode, types_array_struct[mode].astype(
        [(d, '<i8') for d in ('i', 'j', 'k')] +
        [(a, 'O') for a in types_atts[mode]]))
    for mode in modes)

types_array_promo = {
    'var': numpy.array(
        [[0, -2, 0,
          True,
          b'a',
          1.7976931348623157e+308,
          -3.4028234663852886e+38,
          -128.0,
          -32768.0,
          -2147483648.0,
          -9.223372036854776e+18,
          'abcDEF123',
          255.0,
          65535.0,
          4294967295.0,
          1.8446744073709552e+19],
         [1, -2, 0,
          None,
          None,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          None,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan],
         [2, -2, 0,
          None,
          None,
          -numpy.inf,
          numpy.inf,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          None,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan]], dtype=object),
    'fix': numpy.array(
        [[0, -2, 0,
          True,
          b'a',
          1.7976931348623157e+308,
          -3.4028234663852886e+38,
          -128.0,
          -32768.0,
          -2147483648.0,
          -9.223372036854776e+18,
          255.0,
          65535.0,
          4294967295.0,
          1.8446744073709552e+19],
         [1, -2, 0,
          None,
          None,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan],
         [2, -2, 0,
          None,
          None,
          -numpy.inf,
          numpy.inf,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan,
          numpy.nan]], dtype=object),
}

types_shape = {
    'var': ((12, 16), (12, 13)),
    'fix': ((12, 15), (12, 12)),
}


@pytest.fixture(scope='module')
def setup(db):
    for q in types_queries['create']:
        iquery(db, q)

    yield True

    for q in types_queries['clean']:
        iquery(db, q)


class TestTypes:

    @pytest.mark.parametrize(
        ('mode', 'schema'),
        ((mode, schema)
         for mode in modes
         for schema in (None,
                        types_schema[mode],
                        Schema.fromstring(types_schema[mode]))))
    def test_types_numpy(self, db, setup, mode, schema):
        # NumPy array
        ar = iquery(db,
                    'scan(types_{})'.format(mode),
                    fetch=True,
                    as_dataframe=False,
                    schema=schema)
        assert ar.shape == (12,)
        assert ar.ndim == 1
        assert ar[0] == types_array_struct[mode][0]
        assert ar[4] == types_array_struct[mode][1]
        assert ar[8] == types_array_struct[mode][2]

    @pytest.mark.parametrize(
        ('mode', 'schema'),
        ((mode, schema)
         for mode in modes
         for schema in (None,
                        types_schema[mode],
                        Schema.fromstring(types_schema[mode]))))
    def test_types_numpy_atts(self, db, setup, mode, schema):
        # NumPy array, atts_only
        ar = iquery(db,
                    'scan(types_{})'.format(mode),
                    fetch=True,
                    atts_only=True,
                    as_dataframe=False,
                    schema=schema)
        assert ar.shape == (12,)
        assert ar.ndim == 1
        assert ar[0] == types_array_struct[mode][types_atts[mode]][0]
        assert ar[4] == types_array_struct[mode][types_atts[mode]][1]
        assert ar[8] == types_array_struct[mode][types_atts[mode]][2]

    @pytest.mark.parametrize(
        ('mode', 'schema'),
        ((mode, schema)
         for mode in modes
         for schema in (None,
                        types_schema[mode],
                        Schema.fromstring(types_schema[mode]))))
    def test_types_dataframe(self, db, setup, mode, schema):
        # Pandas DataFrame, atts_only
        ar = iquery(db,
                    'scan(types_{})'.format(mode),
                    fetch=True)
        assert ar.shape == types_shape[mode][0]
        assert ar.ndim == 2
        assert numpy.all(ar[0:1].values[0] == types_array_promo[mode][0])

        # Values which differ have to be NAN
        ln = ar[4:5]
        assert pandas.isnull(
            ln[
                ar.columns[
                    (ln.values[0] != types_array_promo[mode][1]).tolist()
                ]]).all().all()

        ln = ar[8:9]
        assert pandas.isnull(
            ln[
                ar.columns[
                    (ln.values[0] != types_array_promo[mode][2]).tolist()
                ]]).all().all()

    @pytest.mark.parametrize(
        ('mode', 'schema'),
        ((mode, schema)
         for mode in modes
         for schema in (None,
                        types_schema[mode],
                        Schema.fromstring(types_schema[mode]))))
    def test_types_dataframe_atts(self, db, setup, mode, schema):
        # Pandas DataFrame, atts_only
        ar = iquery(db,
                    'scan(types_{})'.format(mode),
                    fetch=True,
                    atts_only=True)
        assert ar.shape == types_shape[mode][1]
        assert ar.ndim == 2
        assert numpy.all(ar[0:1].values == types_array_promo[mode][0][3:])

        # Values which differ have to be NAN
        ln = ar[4:5]
        assert pandas.isnull(
                ln[
                    ar.columns[
                        (ln.values != types_array_promo[mode][1][3:])[0]
                    ]]).all().all()

        ln = ar[8:9]
        assert pandas.isnull(
            ln[
                ar.columns[
                    (ln.values != types_array_promo[mode][2][3:])[0]
                ]]).all().all()

    @pytest.mark.parametrize(
        ('mode', 'schema'),
        ((mode, schema)
         for mode in modes
         for schema in (None,
                        types_schema[mode],
                        Schema.fromstring(types_schema[mode]))))
    def test_types_dataframe_no_promo(self, db, setup, mode, schema):
        # Pandas DataFrame, atts_only
        ar = iquery(db,
                    'scan(types_{})'.format(mode),
                    fetch=True,
                    dataframe_promo=False)
        assert ar.shape == types_shape[mode][0]
        assert ar.ndim == 2
        assert ar[0:1].to_records(index=False) == types_array_obj[mode][0]
        assert ar[4:5].to_records(index=False) == types_array_obj[mode][1]
        assert ar[8:9].to_records(index=False) == types_array_obj[mode][2]


pytest_np = numpy.random.randint(1e3, size=10)
pytest_np_null = numpy.array([((255, random.randint(0, 1e3)),)
                              for _ in range(10)],
                             dtype=[('val', [('null', 'u1'), ('val', '<i8')])])


class TestUpload:

    # -- - --
    # -- - IQuery - --
    # -- - --
    @pytest.mark.parametrize(('query', 'upload_schema_str'), [
        (pre + "(pytest_2, '{fn}', 0, '" + fmt + "'" + suf + ')', ups)
        for fmt in ('(int64)', '{fmt}')
        for (pre, suf) in (('store(input', '), pytest_2'),
                           ('insert(input', '), pytest_2'),
                           ('load', ''))
        for ups in ('<val:int64 not null>[i]', None)
    ] + [
        (pre + '(' +
         'input(' + sch + ", '{fn}', 0, '" + fmt + "'), " +
         'pytest_2)', ups)
        for fmt in ('(int64)', '{fmt}')
        for sch in ('<val:int64>[i]', '<val:int64 not null>[i]', '{sch}')
        for pre in ('store',
                    'insert')
        for ups in ('<val:int64 not null>[i]', None)
    ])
    def test_iquery_numpy(self, db, query, upload_schema_str):
        db.create_array('pytest_2', '<val:int64>[i]')
        assert db.iquery(
            query,
            upload_data=pytest_np,
            upload_schema=(Schema.fromstring(upload_schema_str)
                           if upload_schema_str else None)) is None
        db.remove('pytest_2')

    @pytest.mark.parametrize(('query', 'upload_schema_str'), [
        (pre + "(pytest_3, '{fn}', 0, '" + fmt + "'" + suf + ')', ups)
        for fmt in ('(int64 null)', '{fmt}')
        for (pre, suf) in (('store(input', '), pytest_3'),
                           ('insert(input', '), pytest_3'),
                           ('load', ''))
        for ups in ('<val:int64>[i]', None)
    ] + [
        (pre + '(' +
         'input(' + sch + ", '{fn}', 0, '" + fmt + "'), " +
         'pytest_3)', ups)
        for fmt in ('(int64 null)', '{fmt}')
        for sch in ('<val:int64>[i]', '<val:int64 not null>[i]', '{sch}')
        for pre in ('store', 'insert')
        for ups in ('<val:int64>[i]', None)
    ])
    def test_iquery_numpy_null(self, db, query, upload_schema_str):
        db.create_array('pytest_3', '<val:int64>[i]')
        assert db.iquery(
            query,
            upload_data=pytest_np_null,
            upload_schema=(Schema.fromstring(upload_schema_str)
                           if upload_schema_str else None)) is None
        db.remove('pytest_3')

    @pytest.mark.parametrize(('query', 'upload_schema_str'), [
        (pre + "(pytest_4, '{fn}', 0, '" + fmt + "'" + suf + ')', ups)
        for fmt in ('(int64)', '{fmt}')
        for (pre, suf) in (('store(input', '), pytest_4'),
                           ('insert(input', '), pytest_4'),
                           ('load', ''))
        for ups in (['<val:int64 not null>[i]'] +
                    ([None] if fmt[0] != '{' else []))
    ] + [
        ((pre + '(' +
          'input(' + sch + ", '{fn}', 0, '" + fmt + "'), " +
          'pytest_4)'), ups)
        for fmt in ('(int64)', '{fmt}')
        for sch in ('<val:int64>[i]', '<val:int64 not null>[i]', '{sch}')
        for pre in ('store', 'insert')
        for ups in (['<val:int64 not null>[i]'] +
                    ([None] if fmt[0] != '{' and sch[0] != '{' else []))
    ])
    def test_iquery_numpy_bytes(self, db, query, upload_schema_str):
        db.create_array('pytest_4', '<val:int64>[i]')
        assert db.iquery(
            query,
            upload_data=pytest_np,
            upload_schema=(Schema.fromstring(upload_schema_str)
                           if upload_schema_str else None)) is None
        db.remove('pytest_4')

    @pytest.mark.parametrize(('query', 'upload_schema_str'), [
        (pre + "(pytest_5, '{fn}', 0, '" + fmt + "'" + suf + ')',
         ups)
        for fmt in ('(int64 null)', '{fmt}')
        for (pre, suf) in (('store(input', '), pytest_5'),
                           ('insert(input', '), pytest_5'),
                           ('load', ''))
        for ups in (['<val:int64>[i]'] +
                    ([None] if fmt[0] != '{' else []))
    ] + [
        (pre + '(' +
         'input(' + sch + ", '{fn}', 0, '" + fmt + "'), " +
         'pytest_5)',
         ups)
        for fmt in ('(int64 null)', '{fmt}')
        for sch in ('<val:int64>[i]', '<val:int64 not null>[i]', '{sch}')
        for pre in ('store', 'insert')
        for ups in (['<val:int64>[i]'] +
                    ([None] if fmt[0] != '{' and sch[0] != '{' else []))
    ])
    def test_iquery_numpy_null_bytes(self, db, query, upload_schema_str):
        db.create_array('pytest_5', '<val:int64>[i]')
        assert db.iquery(
            query,
            upload_data=pytest_np_null.tobytes(),
            upload_schema=(Schema.fromstring(upload_schema_str)
                           if upload_schema_str else None)) is None
        db.remove('pytest_5')

    # -- - --
    # -- - Input - --
    # -- - --
    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((arr, inp, ins, fmt)) else
         (arr, inp, ins) if all((arr, inp, ins)) else
         (arr, inp) if arr and inp else
         (arr,) if arr else
         (), ups)
        for arr in ('',
                    'pytest_5',
                    'pytest_5_not_null',
                    '<val:int64>[i]',
                    '<val:int64 not null>[i]',
                    '{sch}')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64)'", "'{fmt}'") if ins else (None,))
        for ups in ('<val:int64 not null>[i]', None)
    ])
    def test_input_numpy(self, db, args, upload_schema_str):
        if args and args[0].startswith('pytest_5'):
            if args[0].endswith('not_null'):
                args = ('pytest_5',) + args[1:]
                db.create_array('pytest_5', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_5', '<val:int64>[i]')
        assert type(
            db.input(*args,
                     upload_data=pytest_np,
                     upload_schema=(Schema.fromstring(upload_schema_str)
                                    if upload_schema_str else None)).store(
                                            'pytest_5')) == Array
        db.remove('pytest_5')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((arr, inp, ins, fmt)) else
         (arr, inp, ins) if all((arr, inp, ins)) else
         (arr, inp) if arr and inp else
         (arr,) if arr else
         (), ups)
        for arr in ('',
                    'pytest_6',
                    'pytest_6_not_null',
                    '<val:int64>[i]',
                    '<val:int64 not null>[i]',
                    '{sch}')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64 null)'", "'{fmt}'") if ins else (None,))
        for ups in ('<val:int64>[i]', None)
    ])
    def test_input_numpy_null(self, db, args, upload_schema_str):
        if args and args[0].startswith('pytest_6'):
            if args[0].endswith('not_null'):
                args = ('pytest_6',) + args[1:]
                db.create_array('pytest_6', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_6', '<val:int64>[i]')
        assert type(
            db.input(*args,
                     upload_data=pytest_np_null,
                     upload_schema=(Schema.fromstring(upload_schema_str)
                                    if upload_schema_str else None)).store(
                                            'pytest_6')) == Array
        db.remove('pytest_6')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((arr, inp, ins, fmt)) else
         (arr, inp, ins) if all((arr, inp, ins)) else
         (arr, inp) if arr and inp else
         (arr,) if arr else
         (), ups)
        for arr in ('',
                    'pytest_7',
                    'pytest_7_not_null',
                    '<val:int64>[i]',
                    '<val:int64 not null>[i]',
                    '{sch}')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64)'", "'{fmt}'") if ins else (None,))
        for ups in (['<val:int64 not null>[i]'] +
                    ([None] if (arr == '<val:int64 not null>[i]' or
                                (arr not in ('', '{sch}') and
                                 fmt == "'(int64)'")) else []))
    ])
    def test_input_numpy_bytes(self, db, args, upload_schema_str):
        if args and args[0].startswith('pytest_7'):
            if args[0].endswith('not_null'):
                args = ('pytest_7',) + args[1:]
                db.create_array('pytest_7', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_7', '<val:int64>[i]')
        assert type(
            db.input(*args,
                     upload_data=pytest_np.tobytes(),
                     upload_schema=(Schema.fromstring(upload_schema_str)
                                    if upload_schema_str else None)).store(
                                            'pytest_7')) == Array
        db.remove('pytest_7')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((arr, inp, ins, fmt)) else
         (arr, inp, ins) if all((arr, inp, ins)) else
         (arr, inp) if arr and inp else
         (arr,) if arr else
         (), ups)
        for arr in ('',
                    'pytest_8',
                    'pytest_8_not_null',
                    '<val:int64>[i]',
                    '<val:int64 not null>[i]',
                    '{sch}')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64 null)'", "'{fmt}'") if ins else (None,))
        for ups in (['<val:int64>[i]'] +
                    ([None] if (arr == '<val:int64>[i]' or
                                (arr not in ('', '{sch}') and
                                 fmt == "'(int64 null)'")) else []))
    ])
    def test_input_numpy_null_bytes(self, db, args, upload_schema_str):
        if args and args[0].startswith('pytest_8'):
            if args[0].endswith('not_null'):
                args = ('pytest_8',) + args[1:]
                db.create_array('pytest_8', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_8', '<val:int64>[i]')
        assert type(
            db.input(*args,
                     upload_data=pytest_np_null.tobytes(),
                     upload_schema=(Schema.fromstring(upload_schema_str)
                                    if upload_schema_str else None)).store(
                                            'pytest_8')) == Array
        db.remove('pytest_8')

    def test_input_file(self, db):
        db.build('<x:int64>[i=0:2]', 'i').store('pytest_9')
        db.save('pytest_9', '/tmp/pytest_9')
        db.remove('pytest_9')
        assert type(
            db.input('<x:int64>[i=0:2]', '/tmp/pytest_9').store('pytest_9') ==
            Array)
        db.remove('pytest_9')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((arr, inp, ins, fmt)) else
         (arr, inp, ins) if all((arr, inp, ins)) else
         (arr, inp) if arr and inp else
         (arr,) if arr else
         (), ups)
        for arr in ('',
                    'pytest_10',
                    'pytest_10_not_null',
                    '<val:int64>[i]',
                    '<val:int64 not null>[i]',
                    '{sch}')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64)'", "'{fmt}'") if ins else (None,))
        for ups in ('<val:int64 not null>[i]', None)
    ])
    def test_input_compose(self, db, args, upload_schema_str):
        if args and args[0].startswith('pytest_10'):
            if args[0].endswith('not_null'):
                args = ('pytest_10',) + args[1:]
                db.create_array('pytest_10', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_10', '<val:int64>[i]')
        attr_name = 'val'
        if (not args or args[0].startswith('{')) and not upload_schema_str:
            attr_name = 'x'
        assert type(
            db.store(
                db.input(*args,
                         upload_data=pytest_np,
                         upload_schema=(Schema.fromstring(upload_schema_str)
                                        if upload_schema_str else None)),
                'pytest_10')) == Array
        assert type(
            db.store(
                db.apply(
                    db.input(*args,
                             upload_data=pytest_np,
                             upload_schema=(
                                 Schema.fromstring(upload_schema_str)
                                 if upload_schema_str else None)),
                    'val2', attr_name),
                'pytest_11')) == Array
        db.remove('pytest_10')
        db.remove('pytest_11')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((arr, inp, ins, fmt)) else
         (arr, inp, ins) if all((arr, inp, ins)) else
         (arr, inp) if arr and inp else
         (arr,) if arr else
         (), ups)
        for arr in ('',
                    'pytest_12',
                    'pytest_12_not_null',
                    '<val:int64>[i]',
                    '<val:int64 not null>[i]',
                    '{sch}')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64)'", "'{fmt}'") if ins else (None,))
        for ups in ('<val:int64 not null>[i]', None)
    ])
    def test_input_chain(self, db, args, upload_schema_str):
        is_pytest = False
        if args and args[0].startswith('pytest_12'):
            is_pytest = True
            if args[0].endswith('not_null'):
                args = ('pytest_12',) + args[1:]
                db.create_array('pytest_12', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_12', '<val:int64>[i]')
        attr_name = 'val'
        if (not args or args[0].startswith('{')) and not upload_schema_str:
            attr_name = 'x'
        assert type(
            db.input(*args,
                     upload_data=pytest_np,
                     upload_schema=(Schema.fromstring(upload_schema_str)
                                    if upload_schema_str else None)).apply(
                                            'val2', attr_name).store(
                                                'pytest_13')) == Array
        if is_pytest:
            db.remove('pytest_12')
        db.remove('pytest_13')

    def test_input_join(self, db):
        assert type(
            db.join(
                db.input(upload_data=pytest_np),
                db.build(
                    '<x:int64 NOT NULL> [i=0:9]', 'i')).store(
                        'pytest_14')) == Array
        assert type(
            db.join(db.build('<x:int64 NOT NULL> [i=0:9]', 'i'),
                    db.input(upload_data=pytest_np)).store(
                        'pytest_14')) == Array
        with pytest.raises(NotImplementedError):
            db.join(db.input(upload_data=pytest_np),
                    db.input(upload_data=pytest_np)).store('pytest_14')
        db.remove('pytest_14')

    # -- - --
    # -- - Load - --
    # -- - --
    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((inp, ins, fmt)) else
         (arr, inp, ins) if inp and ins else
         (arr, inp) if inp else
         (arr,), ups)
        for arr in ('pytest_15', 'pytest_15_not_null')
        for inp in ('', "'{fn}'")
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64)'", "'{fmt}'") if ins else (None,))
        for ups in ('<val:int64 not null>[i]', None)
    ])
    def test_load_numpy(self, db, args, upload_schema_str):
        if args and args[0].startswith('pytest_15'):
            if args[0].endswith('not_null'):
                args = ('pytest_15',) + args[1:]
                db.create_array('pytest_15', '<val:int64 not null>[i]')
            else:
                db.create_array('pytest_15', '<val:int64>[i]')
        assert type(
            db.load('pytest_15',
                    *args[1:],
                    upload_data=pytest_np,
                    upload_schema=(Schema.fromstring(upload_schema_str)
                                   if upload_schema_str else None))) == Array
        db.remove('pytest_15')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((inp, ins, fmt)) else
         (arr, inp, ins) if inp and ins else
         (arr, inp) if inp else
         (arr,), ups)
        for arr in ('pytest_16', 'pytest_16_not_null')
        for inp in ('', "'{fn}'")
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64 null)'", "'{fmt}'") if ins else (None,))
        for ups in ('<val:int64>[i]', None)
    ])
    def test_load_numpy_null(self, db, args, upload_schema_str):
        if args[0].endswith('not_null'):
            args = ('pytest_16',) + args[1:]
            db.create_array('pytest_16', '<val:int64 not null>[i]')
        else:
            db.create_array('pytest_16', '<val:int64>[i]')
        assert type(
            db.load('pytest_16',
                    *args[1:],
                    upload_data=pytest_np_null,
                    upload_schema=(Schema.fromstring(upload_schema_str)
                                   if upload_schema_str else None))) == Array
        db.remove('pytest_16')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((inp, ins, fmt)) else
         (arr, inp, ins) if inp and ins else
         (arr, inp) if inp else
         (arr,), ups)
        for arr in ('pytest_17', 'pytest_17_not_null')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64)'", "'{fmt}'") if ins else (None,))
        for ups in (['<val:int64 not null>[i]'] +
                    ([None] if fmt == "'(int64)'" else []))
    ])
    def test_load_numpy_bytes(self, db, args, upload_schema_str):
        if args[0].endswith('not_null'):
            args = ('pytest_17',) + args[1:]
            db.create_array('pytest_17', '<val:int64 not null>[i]')
        else:
            db.create_array('pytest_17', '<val:int64>[i]')
        assert type(
            db.load(
                *args,
                upload_data=pytest_np.tobytes(),
                upload_schema=(Schema.fromstring(upload_schema_str)
                               if upload_schema_str else None))) == Array
        db.remove('pytest_17')

    @pytest.mark.parametrize(('args', 'upload_schema_str'), [
        ((arr, inp, ins, fmt) if all((inp, ins, fmt)) else
         (arr, inp, ins) if inp and ins else
         (arr, inp) if inp else
         (arr,), ups)
        for arr in ('pytest_18', 'pytest_18_not_null')
        for inp in (('', "'{fn}'") if arr else (None,))
        for ins in (('', '0') if inp else (None,))
        for fmt in (('', "'(int64 null)'", "'{fmt}'") if ins else (None,))
        for ups in (['<val:int64>[i]'] +
                    ([None] if fmt == "'(int64 null)'" else []))
    ])
    def test_load_numpy_null_bytes(self, db, args, upload_schema_str):
        if args[0].endswith('not_null'):
            args = ('pytest_18',) + args[1:]
            db.create_array('pytest_18', '<val:int64 not null>[i]')
        else:
            db.create_array('pytest_18', '<val:int64>[i]')
        assert type(
            db.load(
                *args,
                upload_data=pytest_np_null.tobytes(),
                upload_schema=(Schema.fromstring(upload_schema_str)
                               if upload_schema_str else None))) == Array
        db.remove('pytest_18')

    def test_load_file(self, db):
        db.build('<x:int64>[i=0:2]', 'i').store('pytest_19')
        db.save('pytest_19', '/tmp/pytest_19')
        assert type(
            db.load('pytest_19', '/tmp/pytest_19') == Array)
        db.remove('pytest_19')

    def test_load_non_ascii(self, db):
        data = pandas.DataFrame({'pytest_20': [b'\xc2\xb5'.decode('utf-8') +
                                               'bar']})
        assert type(
            db.input('<pytest_20:string not null>[i]',
                     upload_data=data.to_records(index=False)).store(
                         'pytest_20') == Array)
        db.remove('pytest_20')


class TestCreate:

    # -- - --
    # -- - Create - --
    # -- - --
    @pytest.mark.parametrize(('type_name', 'default', 'compression'), [
        (type_name, default, compression)
        for type_name in ('bool',
                          'char',
                          'int8',
                          'int16',
                          'int32',
                          'int64',
                          'uint8',
                          'uint16',
                          'uint32',
                          'uint64',
                          'string')
        for default in (None, 'null')
        for compression in (None, 'zlib', 'bzlib')

    ])
    def test_input_numpy(self, db, type_name, default, compression):
        schema_str = (
            '<x:{type_name} {default_exp} {compression_exp}>[i=0:9]'.format(
                type_name=type_name,
                default_exp='default {}'.format(default) if default else '',
                compression_exp=("compression '{}'".format(compression)
                                 if compression else '')))
        schema = Schema.fromstring(schema_str)
        assert type(db.create_array('pytest_21', schema) == Array)
        assert type(db.build(schema_str, 'null').store('pytest_21') == Array)
        db.remove('pytest_21')


class TestAdmin:

    def test_admin(self):
        db_admin = connect(admin=True)
        assert db_admin.admin is True

        ar = 'test_admin'
        db_admin.build('<x:double>[i=1:10000;j=1:1000]', 'random()').store(ar)

        st = time.time()

        for _ in range(5):
            th = threading.Thread(
                target=lambda: connect(no_ops=True).iquery(
                    'op_count(sort({}))'.format(ar)))
            th.start()

        time.sleep(5)
        que = """project(
                   filter(
                     list('queries'),
                     query_string='op_count(sort({}))'),
                   query_id)""".format(ar)
        qids = db_admin.iquery_readlines(que)
        while qids:
            for qid in qids:
                try:
                    db_admin.cancel(qid)
                except requests.HTTPError as e:
                    if e.response.status_code == 502:
                        db_admin = connect(admin=True)
                        break
                    elif e.response.status_code != 406:
                        raise e
            time.sleep(5)
            qids = db_admin.iquery_readlines(que)

        # Should finish in less then five minutes
        assert time.time() - st < 5 * 60

        db_admin.remove(ar)
