from collections import OrderedDict
from collections.abc import MutableSet
from itertools import repeat
from typing import Any, Iterable, Iterator


__all__ = ["OrderedSet"]


# TODO add generic type annotation, like OrderedSet[T]

# FIXME what classes should we inherit from?
class _OrderedSet(MutableSet):
    def __init__(self, iterable: Iterable = tuple()) -> None:
        self._data = OrderedDict(zip(iterable, repeat(None)))

    __slots__ = ["_data"]

    def __contains__(self, elem: Any) -> bool:
        return elem in self._data.keys()

    def __iter__(self) -> Iterator:
        yield from self._data.keys()

    def __len__(self) -> int:
        return len(self._data)

    def add(self, elem: Any) -> None:
        self._data[elem] = None

    def discard(self, elem: Any) -> None:
        self._data.pop(elem, None)

    def update(self, iterable: Iterable) -> None:
        self._data.update(zip(iterable, repeat(None)))


# If the Cython-written orderedset (https://github.com/simonpercivall/orderedset) library
# is not available, fallback to the less performant pure Python implementation.
try:
    from orderedset import OrderedSet  # type: ignore
except ImportError:
    OrderedSet = _OrderedSet
