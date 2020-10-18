from collections.abc import Hashable

from hypothesis import given
from hypothesis.strategies import integers, lists, tuples

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
