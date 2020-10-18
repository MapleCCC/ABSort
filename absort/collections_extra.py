from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableSet
from itertools import repeat
from typing import TypeVar


__all__ = ["OrderedSet"]


T = TypeVar("T")


class OrderedSet(MutableSet[T]):
    def __init__(self, iterable: Iterable[T] = tuple()) -> None:
        self._data: dict[T, None] = dict.fromkeys(iterable)

    __slots__ = ["_data"]

    def __contains__(self, elem: T) -> bool:
        return elem in self._data

    def __iter__(self) -> Iterator[T]:
        yield from self._data

    def __len__(self) -> int:
        return len(self._data)

    def __sub__(self, other: Iterable[T]) -> OrderedSet[T]:
        new = self.copy()
        new -= other
        return new

    def __isub__(self, other: Iterable[T]) -> OrderedSet[T]:
        for elem in other:
            self._data.pop(elem, None)

        return self

    def copy(self) -> OrderedSet[T]:
        """ Shallow copy, not deep copy """

        new: OrderedSet[T] = OrderedSet()
        new._data = self._data.copy()

        return new

    def add(self, elem: T) -> None:
        self._data[elem] = None

    def discard(self, elem: T) -> None:
        self._data.pop(elem, None)

    def update(self, iterable: Iterable[T]) -> None:
        self._data.update(zip(iterable, repeat(None)))


# If the Cython-written orderedset (https://github.com/simonpercivall/orderedset) library
# is not available, fallback to the less performant pure Python implementation.
try:
    from orderedset import OrderedSet  # type: ignore
except ImportError:
    pass
