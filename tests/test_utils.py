from collections.abc import Hashable, Iterable
from itertools import tee

from hypothesis import assume, given
from hypothesis.strategies import integers, iterables, lists, tuples

from absort.utils import chenyu, iequal, is_nan

from .strategies import hashables


@given(lists(tuples(integers(), integers())), integers(min_value=2))
def test_chenyu_is_deterministic_plane_points(
    points: list[tuple[int, int]], k: int
) -> None:
    distance = lambda x, y: (x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2

    clusters1 = chenyu(points, distance, k)
    clusters2 = chenyu(points, distance, k)

    assert iequal(clusters1, clusters2, strict=True)


@given(lists(hashables().filter(lambda x: not is_nan(x))), integers(min_value=2))
def test_chenyu_is_deterministic_hashables(points: list[Hashable], k: int) -> None:
    distance = lambda x, y: abs(hash(x) - hash(y))

    clusters1 = chenyu(points, distance, k)
    clusters2 = chenyu(points, distance, k)

    assert iequal(clusters1, clusters2, strict=True)


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
