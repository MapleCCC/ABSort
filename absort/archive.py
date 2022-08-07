import contextlib
from collections.abc import Callable, Hashable, Iterable, Iterator
from functools import partial
from itertools import chain
from types import SimpleNamespace
from typing import Any, Optional, TypeVar, Union

import attrs

from .lfu import LFU
from .lru import LRU


__all__ = [
    "lru_cache_with_key",
    "lfu_cache_with_key",
    "apply",
    "SingleThreadPoolExecutor",
]


T = TypeVar("T")
S = TypeVar("S")


# TODO Add more cache replacement policy implementation
def cache_with_key(
    key: Callable[..., Hashable], maxsize: Optional[int] = 128, policy: str = "LRU"
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    It's like the builtin `functools.lru_cache`, except that it provides customization
    space for the key calculating method and the cache replacement policy.
    """

    @attrs.define
    class CacheInfo:
        hit: int = 0
        miss: int = 0
        maxsize: int = 0
        currsize: int = 0

    class decorator:
        def __init__(self, func: Callable[..., T]) -> None:
            self._func = func

            if policy == "LRU":
                self._cache = LRU(maxsize=maxsize)
            elif policy == "LFU":
                self._cache = LFU(maxsize=maxsize)
            else:
                raise NotImplementedError

            self._hit = self._miss = 0

        __slots__ = ("_func", "_cache", "_hit", "_miss")

        def __call__(self, *args: Any, **kwargs: Any) -> T:
            arg_key = key(*args, **kwargs)
            if arg_key in self._cache:
                self._hit += 1
                return self._cache[arg_key]
            else:
                self._miss += 1
                result = self._func(*args, **kwargs)
                self._cache[arg_key] = result
                return result

        @property
        def __cache__(self) -> Union[LRU, LFU]:
            return self._cache

        def cache_info(self) -> CacheInfo:
            return CacheInfo(self._hit, self._miss, maxsize, self._cache.size)

        def clear_cache(self) -> None:
            self._cache.clear()

    return decorator


lru_cache_with_key = partial(cache_with_key, policy="LRU")
lru_cache_with_key.__doc__ = "It's like the builtin `functools.lru_cache`, except that it provides customization space for the key calculating method."

lfu_cache_with_key = partial(cache_with_key, policy="LFU")
lfu_cache_with_key.__doc__ = "It's like the builtin `functools.lru_cache`, except that it provides customization space for the key calculating method, and it uses LFU, not LRU, as cache replacement policy."


def apply(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """ Equivalent to Haskell's $ operator """
    return fn(*args, **kwargs)


def concat(lists: Iterable[list[T]]) -> list[T]:
    """ Concatenate multiple lists into one list """
    return list(chain(*lists))


@contextlib.contextmanager
def SingleThreadPoolExecutor() -> Iterator[SimpleNamespace]:
    "Return an equivalent to ThreadPoolExecutor(max_workers=1)"
    yield SimpleNamespace(map=map, submit=apply, shutdown=nullfunc)


class compose:
    """ Equivalent to Haskell's . operator """

    def __init__(self, fn1: Callable[[T], S], fn2: Callable[..., T]) -> None:
        self._fn1 = fn1
        self._fn2 = fn2

    __slots__ = ("_fn1", "_fn2")

    def __call__(self, *args: Any, **kwargs: Any) -> S:
        return self._fn1(self._fn2(*args, **kwargs))


def nullfunc(*_: Any, **__: Any) -> None:
    """ A function that does nothing """
    pass
