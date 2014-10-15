from __future__ import print_function, absolute_import, unicode_literals
import logging

from .robust import cross_join
from .utils import interleave, as_list, _new_attribute_label
from . import schema_utils as su


def _prepare_join_schema(left, right, left_on, right_on):

    new_left = list(left_on)
    new_right = list(right_on)

    dt = dict((nm, typ) for nm, typ, _ in left.sdbtype.full_rep)
    f = left.afl
    sdb = left.interface

    # create categorical variables for attributes that cant be cast to
    # integers. Update join lists
    for i, (l, r) in enumerate(zip(left_on, right_on)):
        if l not in dt or 'int' in dt[l]:
            continue

        left_att = _new_attribute_label('%s_idx' % l, left)
        right_att = _new_attribute_label('%s_idx' % r, right)

        # compute the union of key values
        logging.getLogger(__name__).debug('Build category variable 1')
        lidx = su.boundify(f.uniq(f.sort(left[l]).eval()).eval())
        logging.getLogger(__name__).debug('Build category variable 2')
        ridx = su.boundify(f.uniq(f.sort(right[r])).eval()).eval()
        logging.getLogger(__name__).debug('Rename')
        ridx = ridx.attribute_rename(ridx.att_names[0], lidx.att_names[0]).eval()
        logging.getLogger(__name__).debug('Join')
        idx = f.uniq(f.sort(sdb.hstack((lidx, ridx))))

        logging.getLogger(__name__).debug('index lookup L')
        left = f.index_lookup(left.as_('L'),
                              idx,
                              'L.%s' % l,
                              left_att,
                              "'index_sorted=true'")
        new_left[i] =  left_att

        logging.getLogger(__name__).debug('index lookup R')
        right = f.index_lookup(right.as_('R'),
                               idx,
                               'R.%s' % r,
                               right_att,
                               "'index_sorted=true'")
        new_right[i] =  right_att

    # promote join attributes to dimensions
    logging.getLogger(__name__).debug('dimensionify')
    left = su.to_dimensions(left, *new_left)
    right = su.to_dimensions(right, *new_right)

    return left, right, new_left, new_right

def _apply_suffix(left, right, left_on, right_on, suffixes):
    """
    Fully disambiguate left and right schemas by applying suffixes.

    Returns
    -------
    new_left, new_right, new_left_on, new_right_on
    """
    lnames = set(left.att_names) | set(left.dim_names)
    rnames = set(right.att_names) | set(right.dim_names)

    # add suffix to join column names
    left_on_old = list(left_on)
    left_on = [l if l not in right_on else l + suffixes[0]
               for l in left_on]
    right_on = [r if r not in left_on_old else r + suffixes[1]
                for r in right_on]

    duplicates = list(lnames & rnames)

    def _relabel(x, dups, suffix):
        x = x.attribute_rename(*(item for d in dups if d in x.att_names
                                 for item in (d, d + suffix)))
        x = x.dimension_rename(*(item for d in dups if d in x.dim_names
                                 for item in (d, d + suffix)))
        return x

    return (_relabel(left, duplicates, suffixes[0]),
            _relabel(right, duplicates, suffixes[1]),
            left_on, right_on)


def merge(left, right, on=None, left_on=None, right_on=None,
          how='inner', suffixes=('_x', '_y')):
    """
    Perform a pandas-like join on two SciDBArrays.

    Parameters
    ----------
    left : SciDBArray
       The left array to join on
    right : SciDBArray
       The right array to join on
    on : None, string, or list of strings
       The names of dimensions or attributes to join on. Either
       on or both `left_on` and `right_on` must be supplied.
       If on is supplied, the specified names must exist in both
       left and right
    left_on : None, string, or list of strings
        The names of dimensions or attributes in the left array to join on.
        If provided, then right_on must also be provided, and have as many
        elements as left_on
    right_on : None, string, or list of strings
        The name of dimensions or attributes in the right array to join on.
        See notes above for left_join
    how : 'inner' | 'left' | 'right' | 'outer'
        The kind of join to perform. Currently, only 'inner' is supported.
    suffixes : tuple of two strings
        The suffix to add to array dimensions or attributes which
        are duplicated in left and right.

    Returns
    -------
    joined : SciDBArray
       The new SciDB array. The new array has a single dimension,
       and an attribute for each attribute + dimension in left and right.
       The order of rows in the result is unspecified.

    Examples
    --------

    In [15]: authors
    Out[15]:
    array([('Tukey', 'US', True), ('Venables', 'Australia', False),
           ('Tierney', 'US', False), ('Ripley', 'UK', False),
           ('McNeil', 'Australia', False)],
          dtype=[('surname', 'S10'), ('nationality', 'S10'), ('deceased', '?')])

    In [16]: books
    Out[16]:
    array([('Exploratory Data Analysis', 'Tukey'),
           ('Modern Applied Statistics ...', 'Venables'),
           ('LISP-STAT', 'Tierney'), ('Spatial Statistics', 'Ripley'),
           ('Stochastic Simulation', 'Ripley'),
           ('Interactive Data Analysis', 'McNeil'),
           ('Python for Data Analysis', 'McKinney')],
          dtype=[('title', 'S40'), ('name', 'S10')])

    In [17]: a = sdb.from_array(authors)
    In [18]: b = sdb.from_array(books)
    In [19]: sdb.join(a, b, left_on='surname', right_on='name').todataframe()
    Out[19]:
          i0_x  i0_y   surname nationality deceased                          title
    _row
    0        0     0     Tukey          US     True      Exploratory Data Analysis
    1        1     1  Venables   Australia    False  Modern Applied Statistics ...
    2        2     2   Tierney          US    False                      LISP-STAT
    3        3     3    Ripley          UK    False             Spatial Statistics
    4        3     4    Ripley          UK    False          Stochastic Simulation
    5        4     5    McNeil   Australia    False      Interactive Data Analysis

    Notes
    -----
    This function wraps the SciDB cross_join operator, but performs several
    preprocessing steps::

      - Attributes are converted into dimensions automatically
      - Chunk size and overlap is standardized
      - Joining on non-integer attributes is handled using index_lookup
    """

    lnames = set(left.att_names) | set(left.dim_names)
    rnames = set(right.att_names) | set(right.dim_names)

    if how != 'inner':
        raise NotImplementedError("Only inner joins are supported for now.")

    if (left_on is not None or right_on is not None) and on is not None:
        raise ValueError("Cannot specify left_on/right_on with on")

    if left_on is not None or right_on is not None:
        if left_on is None or right_on is None:
            raise ValueError("Must specify both left_on and right_on")

        left_on = as_list(left_on)
        right_on = as_list(right_on)
        if len(left_on) != len(right_on):
            raise ValueError("left_on and right_on must have "
                             "the same number of items")

    else:
        on = on or list(lnames & rnames)
        on = as_list(on)
        left_on = right_on = on

    for l in left_on:
        if l not in lnames:
            raise ValueError("Left array join name is invalid: %s" % l)
    for r in right_on:
        if r not in rnames:
            raise ValueError("Right array join name is invalid: %s" % r)

    # fully disambiguate arrays
    logging.getLogger(__name__).debug("Applying suffixes")
    left_on_orig = left_on
    left, right, left_on, right_on = _apply_suffix(left, right,
                                                   left_on, right_on,
                                                   suffixes)

    keep = (set(left.att_names) | set(left.dim_names)
            | set(right.dim_names) | set(right.att_names))
    keep = keep - set(right_on)

    # build necessary dimensions to join on
    # XXX push this logic into cross_join
    logging.getLogger(__name__).debug("Preparing categorical attributes")
    left, right, left_on, right_on = _prepare_join_schema(left, right, left_on, right_on)

    logging.getLogger(__name__).debug("Performing cross join")
    result = cross_join(left, right, *interleave(left_on, right_on))

    # throw away index dimensions added by _prepare_join_schema
    logging.getLogger(__name__).debug("Dropping supurious attributes")
    idx = _new_attribute_label('_row', result)
    result = result.unpack(idx)
    result = result.project(*(a for a in result.att_names if a in keep))

    # drop suffixes if they aren't needed
    logging.getLogger(__name__).debug("Dropping suffixes")
    renames = []
    for a in result.att_names:
        if not a.endswith(suffixes[0]):
            continue

        if a.replace(suffixes[0], suffixes[1]) not in result.att_names:
            renames.extend((a, a.replace(suffixes[0], '')))

    result = result.attribute_rename(*renames)
    return result