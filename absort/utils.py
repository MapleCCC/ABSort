import contextlib
import difflib
import functools
import itertools
import os
import typing
import sys
from collections import OrderedDict, namedtuple
from functools import partial
from types import SimpleNamespace
from typing import (
    IO,
    Any,
    Callable,
    Hashable,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    TypeVar,
    overload,
)

from colorama import Fore, Style

from .lfu import LFU
from .lru import LRU

__all__ = [
    "ireverse",
    "xreverse",
    "beginswith",
    "bright_red",
    "bright_green",
    "bright_blue",
    "bright_yellow",
    "colored_unified_diff",
    "cached_splitlines",
    "silent_context",
    "lru_cache_with_key",
    "lfu_cache_with_key",
    "apply",
    "first_true",
    "Logger",
    "concat",
    "SingleThreadPoolExecutor",
    "compose",
    "whitespace_lines",
    "dispatch",
    "duplicated",
]

# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


_T = TypeVar("_T")
_S = TypeVar("_S")


@overload
def ireverse(iterable: Iterable[_T]) -> Iterator[_T]:
    ...


def ireverse(iterable: Iterable) -> Iterator:
    """
    Similar to the builtin function reversed(), except accept iterable objects as input
    """
    l = list(iterable)
    for i in range(len(l)):
        yield l[~i]


@overload
def xreverse(iterable: Iterable[_T]) -> List[_T]:
    ...


def xreverse(iterable: Iterable) -> List:
    """
    Similar to the builtin function reversed(), except accept iterable objects as input,
    and return non-lazy result
    """
    return list(iterable)[::-1]


def beginswith(s: str, prefix: str) -> bool:
    """ Inverse of the `str.endswith` method """

    if len(s) < len(prefix):
        return False
    else:
        return s[: len(prefix)] == prefix


def bright_red(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright red color.
    """
    return Style.BRIGHT + Fore.RED + s + Style.RESET_ALL  # type: ignore


def bright_green(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright green color.
    """
    return Style.BRIGHT + Fore.GREEN + s + Style.RESET_ALL  # type: ignore


def bright_blue(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright blue color.
    """
    return Style.BRIGHT + Fore.BLUE + s + Style.RESET_ALL  # type: ignore


def bright_yellow(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright yellow color.
    """
    return Style.BRIGHT + Fore.YELLOW + s + Style.RESET_ALL  # type: ignore


def colored_unified_diff(
    a: List[str], b: List[str], *args: Any, **kwargs: Any
) -> Iterator[str]:
    """ Return unified diff view between a and b, with color """

    for line in difflib.unified_diff(a, b, *args, **kwargs):
        code = line[0]
        if line[:3] in ("---", "+++") or line[:2] == "@@":
            # Control lines
            yield line
        elif code == " ":
            yield line
        elif code == "+":
            yield bright_green(line)
        elif code == "-":
            yield bright_red(line)
        else:
            raise RuntimeError("Unreachable")


@functools.lru_cache(maxsize=None)
def cached_splitlines(s: str) -> List[str]:
    """ A cached version of the `str.splitlines` method """
    return s.splitlines()


@contextlib.contextmanager
def silent_context() -> Iterator:
    """
    Return a context manager. Within the context, writting to `stdout` is discarded.
    """

    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, "a")
    # sys.stderr = open(os.devnull, "a")
    try:
        yield
    finally:
        sys.stdout = original_stdout


# TODO Add more cache replacement policy implementation
def cache_with_key(
    key: Callable[..., Hashable], maxsize: Optional[int] = 128, policy: str = "LRU"
) -> Callable[[Callable[..., _T]], Callable[..., _T]]:
    """
    It's like the builtin `functools.lru_cache`, except that it provides customization
    space for the key calculating method and the cache replacement policy.
    """

    def decorator(fn: Callable[..., _T]) -> Callable[..., _T]:
        if policy == "LRU":
            _cache = LRU(maxsize=maxsize)
        elif policy == "LFU":
            _cache = LFU(maxsize=maxsize)
        else:
            raise NotImplementedError

        CacheInfo = namedtuple("CacheInfo", ["hit", "miss", "maxsize", "currsize"])
        hit = miss = 0

        @functools.wraps(fn)
        @profile  # type: ignore
        def wrapper(*args: Any, **kwargs: Any) -> _T:
            arg_key = key(*args, **kwargs)
            if arg_key in _cache:
                nonlocal hit
                hit += 1
                return _cache[arg_key]
            else:
                nonlocal miss
                miss += 1
                result = fn(*args, **kwargs)
                _cache[arg_key] = result
                return result

        wrapper.__cache__ = _cache
        wrapper.cache_info = lambda: CacheInfo(hit, miss, maxsize, _cache.size)
        wrapper.clear_cache = _cache.clear

        return wrapper

    return decorator


lru_cache_with_key = partial(cache_with_key, policy="LRU")
lru_cache_with_key.__doc__ = "It's like the builtin `functools.lru_cache`, except that it provides customization space for the key calculating method."

lfu_cache_with_key = partial(cache_with_key, policy="LFU")
lfu_cache_with_key.__doc__ = "It's like the builtin `functools.lru_cache`, except that it provides customization space for the key calculating method, and it uses LFU, not LRU, as cache replacement policy."


def apply(fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    """ Equivalent to Haskell's $ operator """
    return fn(*args, **kwargs)


@overload
def first_true(
    iterable: Iterable[_T], *, default: Any = None, pred: Callable[[_T], bool] = None
) -> Any:
    ...


def first_true(
    iterable: Iterable, *, default: Any = None, pred: Callable[..., bool] = None
) -> Any:
    """ Equivalent to more-itertools library's `first_true` function """

    if pred is None:
        pred = bool
    for elem in iterable:
        if pred(elem):
            return elem
    return default


class Logger:
    """
    A lightweight logger.

    It's just a thin wrapper over the builtin print function, except that it prints
    strings with order numbers prepended.
    """

    def __init__(self) -> None:
        self._count = 1

    __slots__ = "_count"

    def log(self, s: str, file: IO = sys.stdout) -> None:
        """
        It's just a thin wrapper over the builtin print function, except that it prints
        strings with order numbers prepended.
        """
        print(bright_green(str(self._count) + ". ") + s, file=file)
        self._count += 1


@overload
def concat(lists: Iterable[List[_T]]) -> List[_T]:
    ...


def concat(lists: Iterable[List]) -> List:
    """ Concatenate multiple lists into one list """
    return list(itertools.chain.from_iterable(lists))


@contextlib.contextmanager
def SingleThreadPoolExecutor() -> Iterator[SimpleNamespace]:
    "Return an equivalent to ThreadPoolExecutor(max_workers=1)"
    yield SimpleNamespace(map=map, submit=apply, shutdown=lambda: None)


class compose:
    """ Equivalent to Haskell's . operator """

    def __init__(self, fn1: Callable[[_T], _S], fn2: Callable[..., _T]) -> None:
        self._fn1 = fn1
        self._fn2 = fn2

    __slots__ = ("_fn1", "_fn2")

    def __call__(self, *args: Any, **kwargs: Any) -> _S:
        return self._fn1(self._fn2(*args, **kwargs))


def whitespace_lines(lines: List[str]) -> bool:
    """ Return whether lines are all whitespaces """
    return all(not line.strip() for line in lines)


Predicate = Callable[[Any], bool]


class dispatch:
    """
    Similar to the functools.singledispatch, except that it uses predicates to dispatch.
    """

    def __init__(self, base_func: Callable) -> None:
        self._regsitry: typing.OrderedDict[Predicate, Callable]
        self._registry = OrderedDict()

        self._base_func = base_func

    __slots__ = ["_registry", "_base_func"]

    def __call__(self, *args):
        if not args:
            raise ValueError

        # For OrderedDict, the iteration order is LIFO
        for predicate, func in self._registry.items():
            if predicate(args[0]):
                return func(*args)

        # Fall back to the base function
        return self._base_func(*args)

    def register(self, predicate: Predicate) -> Callable:
        def decorator(func: Callable) -> Callable:

            if predicate in self._registry:
                raise RuntimeError(
                    f"More than one functions are registered for {predicate}"
                )

            self._registry[predicate] = func

            # Return the orginal function to enable decorator stacking
            return func

        return decorator


def duplicated(sequence: Sequence) -> bool:
    """
    Determine if a sequence contains duplicate elements
    """

    try:
        return len(set(sequence)) < len(sequence)
    except TypeError:
        seen = []
        for elem in sequence:
            if elem in seen:
                return True
            else:
                seen.append(elem)
        return False
