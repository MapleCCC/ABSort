from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableSet
from itertools import repeat
from operator import attrgetter
from typing import Generic, TypeVar

import attr

from .utils import maxmin


__all__ = ["OrderedSet", "UnionFind"]


T = TypeVar("T")


class OrderedSet(MutableSet[T]):
    def __init__(self, iterable: Iterable[T] = tuple()) -> None:
        self._data: dict[T, None] = dict.fromkeys(iterable)

    __slots__ = "_data"

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


@attr.s(auto_attribs=True, slots=True)
class UnionFindNode(Generic[T]):
    item: T
    parent: UnionFindNode[T]
    rank: int = 0


class UnionFind(Generic[T]):
    def __init__(self, elements: Iterable[T]) -> None:
        self._table = {}

        for elem in elements:
            node = UnionFindNode(elem, parent=None)  # type: ignore
            node.parent = node
            self._table[elem] = node

    __slots__ = "_table"

    def find(self, element: T) -> T:
        if element not in self._table:
            raise ValueError(f"Can't find {element}")

        return self._find(self._table[element]).item

    def _find(self, node: UnionFindNode[T]) -> UnionFindNode[T]:
        if node.parent == node:
            return node
        else:
            root = self._find(node.parent)
            node.parent = root
            return root

    def union(self, x: T, y: T) -> None:
        if x not in self._table:
            raise ValueError(f"Can't find {x}")
        if y not in self._table:
            raise ValueError(f"Can't find {y}")

        node1, node2 = self._table[x], self._table[y]
        root1, root2 = self._find(node1), self._find(node2)

        if root1 == root2:
            return
        elif root1.rank != root2.rank:
            root1, root2 = maxmin(root1, root2, key=attrgetter("rank"))
            root2.parent = root1
        else:
            root2.parent = root1
            root1.rank += 1
