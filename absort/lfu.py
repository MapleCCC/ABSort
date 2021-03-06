from __future__ import annotations

import math
from collections.abc import Iterator
from typing import Generic, Optional, TypeVar

__all__ = ["LFU"]


T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")


# A singleton object to denote an element with maximum priority in PriorityQueue
max_priority_sentinel = object()


class PriorityQueue(Generic[T]):
    """ A min-heap """

    def __init__(self) -> None:
        self._storage: list[T] = []
        self._priority_table: dict[T, int] = dict()
        self._priority_table[max_priority_sentinel] = math.inf  # type: ignore

    __slots__ = ("_storage", "_priority_table")

    @property
    def size(self) -> int:
        return len(self._storage)

    def increment(self, elem: T) -> None:
        if elem in self._priority_table:
            self._priority_table[elem] += 1
            index = self._storage.index(elem)
            self._down(index)
        else:
            self._priority_table[elem] = 0
            self._storage.append(elem)
            self._up(len(self._storage) - 1)

    def _up(self, index: int) -> None:
        if index == 0:
            return

        elem = self._storage[index]

        parent_idx = index // 2
        parent = self._storage[parent_idx]

        if self._priority_table[elem] >= self._priority_table[parent]:
            return

        self._storage[parent_idx] = elem
        self._storage[index] = parent
        self._up(parent_idx)

    def _down(self, index: int) -> None:
        elem = self._storage[index]

        left_idx = (index + 1) * 2 - 1
        right_idx = (index + 1) * 2
        if left_idx > len(self._storage) - 1:
            left = max_priority_sentinel
        else:
            left = self._storage[left_idx]
        if right_idx > len(self._storage) - 1:
            right = max_priority_sentinel
        else:
            right = self._storage[right_idx]

        if self._priority_table[left] <= self._priority_table[right]:
            if self._priority_table[elem] <= self._priority_table[left]:
                return
            else:
                self._storage[left_idx] = elem
                self._storage[index] = left
                self._down(left_idx)
        else:
            if self._priority_table[elem] <= self._priority_table[right]:
                return
            else:
                self._storage[right_idx] = elem
                self._storage[index] = right
                self._down(right_idx)

    def pop(self) -> T:
        if self.size == 0:
            raise IndexError("pop from empty PriorityQueue")

        elem = self._storage[0]
        del self._priority_table[elem]
        if len(self._storage) == 1:
            self._storage.clear()
        else:
            self._storage[0] = self._storage.pop()
            self._down(0)
        return elem

    def top(self) -> T:
        if self.size == 0:
            raise IndexError("empty PriorityQueur has no top")

        return self._storage[0]

    def clear(self) -> None:
        self._storage.clear()
        self._priority_table.clear()
        self._priority_table[max_priority_sentinel] = math.inf  # type: ignore

    def copy(self) -> PriorityQueue[T]:
        new: PriorityQueue[T] = PriorityQueue()
        new._storage = self._storage.copy()
        new._priority_table = self._priority_table.copy()
        return new

    def __iter__(self) -> Iterator[T]:
        temp = self.copy()
        while temp.size:
            yield temp.pop()


class LFU(Generic[KT, VT]):
    """ A lightweight and efficient data structure that implements the LFU mechanism. """

    def __init__(self, maxsize: Optional[int] = 128) -> None:
        if maxsize is None:
            maxsize = math.inf  # type: ignore
        if maxsize <= 0:
            raise ValueError("maxsize shoule be positive number")
        self._maxsize: int = maxsize  # type: ignore

        self._storage: dict[KT, VT] = dict()
        self._frequency: PriorityQueue[KT] = PriorityQueue()

    __slots__ = ("_maxsize", "_storage", "_frequency")

    @property
    def size(self) -> int:
        return len(self._storage)

    def __str__(self) -> str:
        temp = []
        for elem in self._frequency:
            temp.append(f"{elem}: {self._storage[elem]}")
        content = ", ".join(temp)
        return "LFU({" + content + "})"

    __repr__ = __str__

    def __setitem__(self, key: KT, value: VT) -> None:
        self._frequency.increment(key)
        self._storage[key] = value

        if self.size > self._maxsize:
            evicted = self._frequency.pop()
            del self._storage[evicted]

    def __getitem__(self, key: KT) -> VT:
        try:
            return self._storage[key]
        except KeyError:
            raise KeyError(f"{key} not in LFU")

    def __contains__(self, key: KT) -> bool:
        return key in self._storage

    def clear(self) -> None:
        self._storage.clear()
        self._frequency.clear()


if __name__ == "__main__":
    lfu = LFU()
    lfu[0] = 1
    lfu[1] = 2
    print(lfu)
