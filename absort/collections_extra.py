from __future__ import annotations

from collections.abc import Iterable, Iterator, Set, MutableSet
from dataclasses import dataclass, field
from functools import total_ordering
from heapq import heappop, heappush
from itertools import repeat
from operator import attrgetter
from typing import Generic, TypeVar

import attrs

from .typing_extra import Comparable
from .utils import maxmin


__all__ = ["OrderedSet", "OrderedFrozenSet", "UnionFind", "PriorityQueue"]


T = TypeVar("T")


class OrderedSet(MutableSet[T]):
    def __init__(self, iterable: Iterable[T] = tuple()) -> None:
        self._data = dict.fromkeys(iterable)  # type: dict[T, None]

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


class OrderedFrozenSet(Set[T]):
    def __init__(self, iterable: Iterable[T]) -> None:
        self._data = dict.fromkeys(iterable)  # type: dict[T, None]

    __slots__ = "_data"

    def __contains__(self, item: T) -> bool:
        return item in self._data

    def __iter__(self) -> Iterator[T]:
        yield from self._data

    def __len__(self) -> int:
        return len(self._data)

    def __hash__(self) -> int:
        return hash(tuple(self._data))


@attrs.define
class UnionFindNode(Generic[T]):
    item: T
    parent: UnionFindNode[T]
    rank: int = 0


class UnionFind(Generic[T]):
    def __init__(self, elements: Iterable[T]) -> None:
        self._table = {}

        for elem in elements:
            node = UnionFindNode(elem, parent=None)
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


@total_ordering
class OrderedBox(Generic[T]):
    def __init__(self, item: T, reverse: bool = False) -> None:
        self._item = item
        self._reverse = reverse

    __slots__ = ("_item", "_reverse")

    def unbox(self) -> T:
        return self._item

    def __eq__(self, other) -> bool:
        if not isinstance(other, OrderedBox):
            return NotImplemented

        return self._item == other._item

    def __lt__(self, other) -> bool:
        if not isinstance(other, OrderedBox):
            return NotImplemented

        if not self._reverse:
            return self._item < other._item
        else:
            return self._item > other._item


@dataclass(order=True)
class PrioritizedItem(Generic[T]):
    priority: Comparable
    item: T = field(compare=False)


class PriorityQueue(Generic[T]):
    def __init__(self, reverse: bool = False) -> None:
        self._reverse = reverse
        self._data = []  # type: list[PrioritizedItem[T]]

    __slots__ = ("_reverse", "_data")

    def __bool__(self) -> bool:
        return bool(self._data)

    def top(self) -> T:
        if not self._data:
            raise IndexError("Empty priority queue has no top")

        return self._data[0].item

    def push(self, elem: T, priority: Comparable) -> None:
        boxed_priority = OrderedBox(priority, reverse=self._reverse)
        pitem = PrioritizedItem(priority=boxed_priority, item=elem)
        heappush(self._data, pitem)

    def pop(self) -> T:
        if not self._data:
            raise IndexError("Pop from empty priority queue")

        return heappop(self._data).item

    def to_iterator(self) -> Iterator[T]:
        """ Destructive """

        while self._data:
            yield heappop(self._data).item
