from typing import Any, List, Tuple

from hypothesis import given
from hypothesis.strategies import from_type, lists, tuples

from absort.lfu import LFU

# TODO we need to test on LFU after random sequence of update/evict operations.


anys = lambda: from_type(type)


@given(lists(anys()))
def test_size(l: List[Any]) -> None:
    lfu = LFU(maxsize=None)
    for elem in l:
        lfu[elem] = None
    assert lfu.size == len(set(l))


@given(lists(anys()))
def test_contains(l: List[Any]) -> None:
    lfu = LFU(maxsize=None)
    for elem in l:
        lfu[elem] = None
    for elem in l:
        assert elem in lfu


@given(lists(tuples(anys(), anys())))
def test_setitem_getitem(l: List[Tuple[Any, Any]]) -> None:
    lfu = LFU(maxsize=None)
    for key, value in l:
        lfu[key] = value
    d = dict(l)
    for key, value in d.items():
        assert lfu[key] == d[key]


@given(lists(anys()))
def test_clear(l: List[Any]) -> None:
    lfu = LFU(maxsize=None)
    for elem in l:
        lfu[elem] = None
    lfu.clear()
    assert lfu.size == 0
    for elem in l:
        assert elem not in lfu
