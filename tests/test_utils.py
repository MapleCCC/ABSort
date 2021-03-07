from collections.abc import  Iterable
from itertools import tee

from hypothesis import assume, given
from hypothesis.strategies import integers, iterables, lists

from absort.utils import iequal


@given(iterables(integers(), max_size=1000), integers(min_value=2, max_value=100))
def test_iequal_equal(iterable: Iterable[int], length: int) -> None:
    iterables = tee(iterable, length)
    assert iequal(*iterables, strict=True)


@given(lists(iterables(integers(), max_size=1000), min_size=2))
def test_iequal_unequal(iterables: list[Iterable[int]]) -> None:
    ls = set((*iterable,) for iterable in iterables)
    assume(len(ls) > 1)
    iterables = map(iter, ls)
    assert not iequal(*iterables, strict=True)
