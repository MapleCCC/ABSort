from hypothesis import given
from hypothesis.strategies import integers, lists, tuples

from absort.utils import chenyu, iequal


@given(lists(tuples(integers(), integers())), integers(min_value=2))
def test_chenyu_is_deterministic(points: list[tuple[int, int]], k: int)->None:
    distance = lambda x, y: (x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2

    clusters1 = chenyu(points, distance, k)
    clusters2 = chenyu(points, distance, k)

    assert iequal(clusters1, clusters2)
