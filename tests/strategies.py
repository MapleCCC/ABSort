from hypothesis.strategies import (
    binary,
    booleans,
    characters,
    complex_numbers,
    dates,
    datetimes,
    decimals,
    floats,
    fractions,
    from_type,
    functions,
    integers,
    none,
    one_of,
    text,
    timedeltas,
    times,
)

from absort.utils import constantfunc

__all__ = ["anys", "hashables"]


anys = constantfunc(from_type(type))


# TODO add more hashable types to draw from.
# Remember that the less complex one should be located at the front. Quote "In order to get good shrinking behaviour, try to put simpler strategies first" from https://hypothesis.readthedocs.io/en/latest/data.html#hypothesis.strategies.one_of
hashables = constantfunc(
    one_of(
        none(),
        booleans(),
        integers(),
        characters(),
        text(),
        binary(),
        fractions(),
        decimals(),
        floats(),
        complex_numbers(),
        timedeltas(),
        times(),
        dates(),
        datetimes(),
        functions(),
    ).filter(lambda x: not x.is_snan())  # Signaling NaN is unhashable
)
