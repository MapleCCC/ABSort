import contextlib
import difflib
import functools
import itertools
import operator
import os
import sys
from collections import OrderedDict
from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from functools import partial
from itertools import zip_longest
from types import SimpleNamespace
from typing import IO, Any, Optional, TypeVar, Union, overload

import attr
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
    "nth",
    "nths",
    "hamming_distance",
    "strict_splitlines",
    "nullfunc",
    "constantfunc",
    "identifyfunc",
    "iequal",
    "on_except_return",
    "contains",
    "larger_recursion_limit",
    "memoization",
]


T = TypeVar("T")
S = TypeVar("S")


@overload
def ireverse(iterable: Iterable[T]) -> Iterator[T]:
    ...


def ireverse(iterable: Iterable) -> Iterator:
    """
    Similar to the builtin function reversed(), except accept iterable objects as input
    """
    l = list(iterable)
    for i in range(len(l)):
        yield l[~i]


@overload
def xreverse(iterable: Iterable[T]) -> list[T]:
    ...


def xreverse(iterable: Iterable) -> list:
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
    a: list[str], b: list[str], *args: Any, **kwargs: Any
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
def cached_splitlines(s: str) -> list[str]:
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
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    It's like the builtin `functools.lru_cache`, except that it provides customization
    space for the key calculating method and the cache replacement policy.
    """

    @attr.s(auto_attribs=True)
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
            return CacheInfo(self._hit, self._miss, maxsize, self._cache.size)  # type: ignore

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


@overload
def first_true(
    iterable: Iterable[T], *, default: Any = None, pred: Callable[[T], bool] = bool
) -> Any:
    ...


def first_true(
    iterable: Iterable, *, default: Any = None, pred: Callable[..., bool] = bool
) -> Any:
    """ Equivalent to more-itertools library's `first_true` function """

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
def concat(lists: Iterable[list[T]]) -> list[T]:
    ...


def concat(lists: Iterable[list]) -> list:
    """ Concatenate multiple lists into one list """
    return list(itertools.chain.from_iterable(lists))


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


def whitespace_lines(lines: list[str]) -> bool:
    """ Return whether lines are all whitespaces """
    return all(not line.strip() for line in lines)


Predicate = Callable[[Any], bool]


class dispatch:
    """
    Similar to the functools.singledispatch, except that it uses predicates to dispatch.
    """

    def __init__(self, base_func: Callable) -> None:
        self._regsitry: OrderedDict[Predicate, Callable]
        self._registry = OrderedDict()

        self._base_func = base_func

    __slots__ = ["_registry", "_base_func"]

    def __call__(self, *args, **kwargs):
        if not args:
            raise ValueError("There should at least be one positional argument")

        # For OrderedDict, the iteration order is LIFO
        for predicate, func in self._registry.items():
            if predicate(args[0]):
                return func(*args, **kwargs)

        # Fall back to the base function
        return self._base_func(*args, **kwargs)

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


@overload
def nth(iterable: Iterable[T], n: int) -> T:
    ...


def nth(iterable: Iterable, n: int):
    count = 0
    for elem in iterable:
        if count == n:
            return elem
        count += 1
    raise ValueError(f"Iterable doesn't have {n}-th element")


@overload
def nths(iterable: Iterable[Iterable[T]], n: int) -> Iterator[T]:
    ...


def nths(iterable: Iterable, n: int = 0) -> Iterator:
    for sub_iterable in iterable:
        yield nth(sub_iterable, n)


@overload
def hamming_distance(
    iterable1: Iterable[T],
    iterable2: Iterable[S],
    equal: Callable[[T, S], bool] = operator.eq,
) -> int:
    ...


def hamming_distance(
    iterable1: Iterable,
    iterable2: Iterable,
    equal: Callable[[Any, Any], bool] = operator.eq,
) -> int:
    """ Don't apply on infinite iterables """

    sentinel = object()
    distance = 0
    for elem1, elem2 in zip_longest(iterable1, iterable2, fillvalue=sentinel):
        if not equal(elem1, elem2):
            distance += 1
    return distance


# TODO add `keepends` argument
def strict_splitlines(s: str) -> list[str]:
    """
    Similar to the str.splilines() function, except that the line boundaries are NOT a
    superset of universal newlines.
    """

    if not s:
        return []

    res = s.split("\n")
    if res[-1] == "":
        res = res[:-1]
    return res


def nullfunc(*_: Any, **__: Any) -> None:
    """ A function that does nothing """
    pass


def constantfunc(const: T) -> Callable[..., T]:
    """ A constant function """

    def func(*_: Any, **__: Any) -> T:
        return const

    return func


def identityfunc(input: T) -> T:
    """ An identity function """
    return input


def iequal(
    iterable1: Iterable,
    iterable2: Iterable,
    equal: Callable[[Any, Any], bool] = operator.eq,
    strict: bool = False,
) -> bool:
    if not strict:
        return all(map(equal, iterable1, iterable2))
    else:
        list1 = list(iterable1)
        list2 = list(iterable2)
        return len(list1) == len(list2) and all(map(equal, list1, list2))


class on_except_return:
    def __init__(self, exception: type[Exception], returns: Any = None) -> None:
        self._exception = exception
        self._return = returns

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except self._exception:
                return self._return

        return wrapper


def contains(
    container: Any, elem: Any, equal: Callable[[Any, Any], bool] = operator.eq
) -> bool:
    return any(equal(elem, value) for value in container)


@contextlib.contextmanager
def larger_recursion_limit() -> Iterator:
    orig_rec_limit = sys.getrecursionlimit()

    # 2147483647 is the largest integer that sys.setrecursionlimit() accepts in my development environment.
    # FIXME Does the Python language specification say anything about the largest number acceptable as argument to sys.setrecursionlimit()?
    sys.setrecursionlimit(2147483647)

    try:
        yield
    finally:
        sys.setrecursionlimit(orig_rec_limit)


def memoization(
    key: Callable[..., Hashable]
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """ A decorator to apply memoization to function """

    @attr.s(auto_attribs=True)
    class CacheInfo:
        hit: int = 0
        miss: int = 0
        currsize: int = 0

    class decorator:
        def __init__(self, func: Callable[..., T]) -> None:
            self._func = func
            self._cache: dict[Any, T] = {}
            self._hit = 0
            self._miss = 0

        __slots__ = ("_func", "_cache", "_hit", "_miss")

        def __call__(self, *args, **kwargs) -> T:
            args_key = key(*args, **kwargs)

            if args_key in self._cache:
                return self._cache[args_key]
            else:
                result = self._func(*args, **kwargs)
                self._cache[args_key] = result
                return result

        @property
        def __cache__(self) -> dict[Any, T]:
            return self._cache

        def clear_cache(self) -> None:
            self._cache.clear()

        def cache_info(self) -> CacheInfo:
            return CacheInfo(self._hit, self._miss, len(self._cache))  # type: ignore

    return decorator
