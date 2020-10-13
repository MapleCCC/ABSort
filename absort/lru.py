from __future__ import annotations

import math
from typing import Generic, Optional, TypeVar


__all__ = ["LRU"]


KT = TypeVar("KT")
VT = TypeVar("VT")


MAXIMUM_RECENCY_LIST_SIZE = 1000


class BogusCell:
    """ A singleton to signal lack of value """

    _singleton = None

    def __new__(cls: type[BogusCell]) -> BogusCell:
        if cls._singleton is None:
            cls._singleton = object.__new__(cls)
        return cls._singleton


# A singleton to signal lack of value
_BOGUS_CELL = BogusCell()


class LRU(Generic[KT, VT]):
    """ An lightweight and efficient data structure that implements the LRU mechanims """

    def __init__(self, maxsize: Optional[int] = 128) -> None:
        if maxsize is None:
            maxsize = math.inf  # type: ignore
        if maxsize <= 0:
            raise ValueError("maxsize should be positive integer")

        self._maxsize: int = maxsize  # type: ignore
        self._storage: dict[KT, VT] = dict()
        self._recency: list[KT] = list()
        self._indexer: dict[KT, int] = dict()
        self._offset: int = 0

    __slots__ = ("_maxsize", "_storage", "_recency", "_indexer", "_offset")

    @property
    def size(self) -> int:
        return len(self._storage)

    def __str__(self) -> str:
        temp = []
        # start with the element with greatest recency
        for key in reversed(self._recency):
            if key is not _BOGUS_CELL:
                temp.append(f"{key}: {self._storage[key]}")
        content = ", ".join(temp)
        return "LRU({" + content + "})"

    __repr__ = __str__

    def __setitem__(self, key: KT, value: VT) -> None:
        if key in self._indexer:
            index = self._indexer[key]
            self._recency[index] = _BOGUS_CELL
        self._recency.append(key)
        self._indexer[key] = len(self._recency) - 1
        self._storage[key] = value

        if self.size > self._maxsize:
            evicted = None
            for idx, key in enumerate(self._recency[self._offset :], self._offset):
                if key is not _BOGUS_CELL:
                    self._recency[idx] = _BOGUS_CELL
                    self._offset = idx + 1
                    evicted = key
                    break

            del self._storage[evicted]
            del self._indexer[evicted]

        if len(self._recency) > MAXIMUM_RECENCY_LIST_SIZE:
            self._reconstruct()

    def __contains__(self, key: KT) -> bool:
        return key in self._storage

    def __getitem__(self, key: KT) -> VT:
        try:
            return self._storage[key]
        except KeyError:
            raise KeyError(f"Key {key} is not in LRU")

    def _reconstruct(self) -> None:
        self._offset = 0
        self._indexer.clear()
        old_recency_list = self._recency
        self._recency.clear()

        for key in old_recency_list:
            if key is not _BOGUS_CELL:
                self._recency.append(key)
                self._indexer[key] = len(self._recency) - 1

    def clear(self) -> None:
        self._storage.clear()
        self._recency.clear()
        self._indexer.clear()
        self._offset = 0


if __name__ == "__main__":
    lru = LRU()
    lru[0] = 1
    lru[1] = 2
    lru[0] = 3
    print(lru)
