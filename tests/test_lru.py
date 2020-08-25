from typing import Any, List, Tuple

from hypothesis import given
from hypothesis.strategies import from_type, lists, tuples

from absort.lru import LRU

# TODO we need to test on LRU after random sequence of update/evict operations.


anys = lambda: from_type(type)


@given(lists(anys()))
def test_size(l: List[Any]) -> None:
    lru = LRU(maxsize=None)
    for elem in l:
        lru[elem] = None
    assert lru.size == len(set(l))


@given(lists(anys()))
def test_contains(l: List[Any]) -> None:
    lru = LRU(maxsize=None)
    for elem in l:
        lru[elem] = None
    for elem in l:
        assert elem in lru


@given(lists(tuples(anys(), anys())))
def test_setitem_getitem(l: List[Tuple[Any, Any]]) -> None:
    lru = LRU(maxsize=None)
    for key, value in l:
        lru[key] = value
    d = dict(l)
    for key, value in d.items():
        assert lru[key] == d[key]


@given(lists(anys()))
def test_clear(l: List[Any]) -> None:
    lru = LRU(maxsize=None)
    for elem in l:
        lru[elem] = None
    lru.clear()
    assert lru.size == 0
    for elem in l:
        assert elem not in lru
