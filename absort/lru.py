from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Type

from .profile_tools import add_profile_decorator_to_class_methods


__all__ = ["LRU"]


MAXIMUM_RECENCY_LIST_SIZE = 1000


class DummyCell:
    """ A singleton to signal lack of value """

    _singleton = None

    def __new__(cls: Type[DummyCell]) -> DummyCell:
        if cls._singleton is None:
            cls._singleton = object.__new__(cls)
        return cls._singleton


# A singleton to signal lack of value
_DUMMY_CELL = DummyCell()


@add_profile_decorator_to_class_methods
class LRU:
    def __init__(self, maxsize: Optional[int] = 128) -> None:
        if maxsize is None:
            maxsize = math.inf  # type: ignore
        if maxsize <= 0:
            raise ValueError("maxsize should be positive integer")
        self._maxsize = maxsize
        self._storage: Dict = dict()
        self._recency: List = list()
        self._indexer: Dict = dict()
        self._offset: int = 0

    __slots__ = ("_maxsize", "_storage", "_recency", "_indexer", "_offset")

    @property
    def size(self) -> int:
        return len(self._storage)

    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self._indexer:
            index = self._indexer[key]
            self._recency[index] = _DUMMY_CELL
        self._recency.append(key)
        self._indexer[key] = len(self._recency) - 1
        self._storage[key] = value

        if self.size > self._maxsize:
            evicted = None
            for idx, key in enumerate(self._recency[self._offset :], self._offset):
                if key is not _DUMMY_CELL:
                    self._recency[idx] = _DUMMY_CELL
                    self._offset = idx + 1
                    evicted = key
                    break

            del self._storage[evicted]
            del self._indexer[evicted]

        if len(self._recency) > MAXIMUM_RECENCY_LIST_SIZE:
            self._reconstruct()

    def __contains__(self, key: Any) -> bool:
        return key in self._storage

    def __getitem__(self, key: Any) -> Any:
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
            if key is not _DUMMY_CELL:
                self._recency.append(key)
                self._indexer[key] = len(self._recency) - 1

    def clear(self) -> None:
        self._storage.clear()
        self._recency.clear()
        self._indexer.clear()
        self._offset = 0
