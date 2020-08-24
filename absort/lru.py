import math
from collections import deque
from typing import Any, Deque, Dict, Optional

from .profile_tools import add_profile_decorator_to_class_methods


__all__ = ["LRU"]


@add_profile_decorator_to_class_methods
class LRU:
    def __init__(self, maxsize: Optional[int] = 128) -> None:
        if maxsize is None:
            maxsize = math.inf  # type: ignore
        if maxsize <= 0:
            raise ValueError("maxsize should be positive integer")
        self._maxsize = maxsize
        self._storage: Dict = dict()
        self._recency: Deque = deque()

    __slots__ = ("_maxsize", "_storage", "_recency")

    @property
    def size(self) -> int:
        return len(self._recency)

    def update(self, key: Any, value: Any) -> None:
        if key in self._storage:
            self._recency.remove(key)
        self._recency.append(key)
        self._storage[key] = value

        if len(self._recency) > self._maxsize:
            to_evict = self._recency.popleft()
            del self._storage[to_evict]

    def __contains__(self, key: Any) -> bool:
        return key in self._storage

    def __getitem__(self, key: Any) -> Any:
        try:
            return self._storage[key]
        except KeyError:
            raise KeyError(f"Key {key} is not in LRU")

    def clear(self) -> None:
        self._storage.clear()
        self._recency.clear()
