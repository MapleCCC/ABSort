import contextlib
import difflib
import functools
import math
import operator
import os
import sys
from collections import OrderedDict
from collections.abc import Callable, Collection, Hashable, Iterable, Iterator, Sequence
from decimal import Decimal
from functools import cache
from itertools import combinations, zip_longest
from numbers import Complex, Number
from typing import IO, Any, Generic, TypeVar

import attr
from colorama import Fore, Style
from more_itertools import UnequalIterablesError, zip_equal

from .exceptions import Unreachable

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
    "Logger",
    "whitespace_lines",
    "dispatch",
    "duplicated",
    "hamming_distance",
    "strict_splitlines",
    "constantfunc",
    "identityfunc",
    "iequal",
    "on_except_return",
    "contains",
    "larger_recursion_limit",
    "memoization",
    "no_color_context",
    "is_nan",
    "is_dtype",
    "maxmin",
]


T = TypeVar("T")
S = TypeVar("S")


def ireverse(iterable: Iterable[T]) -> Iterator[T]:
    """
    Similar to the builtin function reversed(), except accept iterable objects as input
    """
    l = list(iterable)
    for i in range(len(l)):
        yield l[~i]


def xreverse(iterable: Iterable[T]) -> list[T]:
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

    if "NO_COLOR" in os.environ:
        return s

    return Style.BRIGHT + Fore.RED + s + Style.RESET_ALL  # type: ignore


def bright_green(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright green color.
    """

    if "NO_COLOR" in os.environ:
        return s

    return Style.BRIGHT + Fore.GREEN + s + Style.RESET_ALL  # type: ignore


def bright_blue(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright blue color.
    """

    if "NO_COLOR" in os.environ:
        return s

    return Style.BRIGHT + Fore.BLUE + s + Style.RESET_ALL  # type: ignore


def bright_yellow(s: str) -> str:
    """
    Augment a string, so that when printed to console, the string is displayed in bright yellow color.
    """

    if "NO_COLOR" in os.environ:
        return s

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
            raise Unreachable


@contextlib.contextmanager
def silent_context(include_err: bool = False) -> Iterator[None]:
    """
    Return a context manager. Within the context, writting to `stdout` is discarded.
    """

    null_device_fd = open(os.devnull, "a", encoding="utf-8")

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    sys.stdout = null_device_fd
    if include_err:
        sys.stderr = null_device_fd

    try:
        yield

    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr


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


def whitespace_lines(lines: list[str]) -> bool:
    """ Return whether lines are all whitespaces """
    return all(not line.strip() for line in lines)


Predicate = Callable[[Any], bool]


class dispatch:
    """
    Similar to the functools.singledispatch, except that it uses predicates to dispatch.
    """

    def __init__(self, base_func: Callable) -> None:
        self._registry: OrderedDict[Predicate, Callable]
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
        # If elements are unhashable
        seen = []
        for elem in sequence:
            if elem in seen:
                return True
            else:
                seen.append(elem)
        return False


def hamming_distance(
    iterable1: Iterable[T],
    iterable2: Iterable[S],
    equal: Callable[[T, S], bool] = operator.eq,
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
    Similar to the str.splitlines() function, except that the line boundaries are NOT a
    superset of universal newlines.
    """

    # Some edge cases handling is necessary to be as closed to the behavior of str.splitlines() as possible

    if not s:
        return []

    res = s.split("\n")

    if res[-1] == "":
        res.pop()

    return res


def constantfunc(const: T) -> Callable[..., T]:
    """ A constant function """

    def func(*_: Any, **__: Any) -> T:
        return const

    return func


def identityfunc(input: T) -> T:
    """ An identity function """
    return input


def iequal(
    *iterables: Iterable,
    equal: Callable[[Any, Any], bool] = operator.eq,
    strict: bool = False,
) -> bool:

    zip_func = zip_equal if strict else zip

    try:
        for elements in zip_func(*iterables):
            for e1, e2 in combinations(elements, 2):
                if not equal(e1, e2):
                    return False
        return True

    except UnequalIterablesError:
        return False


class on_except_return:
    def __init__(self, exception: type[Exception], returns: Any = None) -> None:
        self._exception = exception
        self._return = returns

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except self._exception:
                return self._return

        return wrapper


def contains(
    container: Collection, elem: Any, equal: Callable[[Any, Any], bool] = operator.eq
) -> bool:
    return any(equal(elem, value) for value in container)


@contextlib.contextmanager
def larger_recursion_limit() -> Iterator:
    orig_rec_limit = sys.getrecursionlimit()

    # 2147483647 is the largest integer that sys.setrecursionlimit() accepts in my development environment.
    # FIXME Does the Python language specification say anything about the largest number acceptable as argument to sys.setrecursionlimit()?
    # Searching on all kinds of documents, it seems the number 2147483647 appears in https://docs.python.org/2.0/ref/integers.html, though it's a Python 2.0 doc.
    sys.setrecursionlimit(2147483647)

    try:
        yield
    finally:
        sys.setrecursionlimit(orig_rec_limit)


def memoization(
    key: Callable[..., Hashable] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    A decorator to apply memoization to function.

    A drop-in replacement of the builtin functools.cache, with the additional feature that the key caculation is customizable.
    """

    if key is None:
        return cache

    @attr.s(auto_attribs=True)
    class CacheInfo:
        hit: int = 0
        miss: int = 0
        currsize: int = 0

    class decorator(Generic[T]):
        def __init__(self, func: Callable[..., T]) -> None:
            self._func = func
            self._cache: dict[Any, T] = {}
            self._hit = 0
            self._miss = 0

        __slots__ = ("_func", "_cache", "_hit", "_miss")

        def __call__(self, *args, **kwargs) -> T:
            args_key = key(*args, **kwargs)

            if args_key in self._cache:
                self._hit += 1
                return self._cache[args_key]
            else:
                self._miss += 1
                result = self._func(*args, **kwargs)
                self._cache[args_key] = result
                return result

        @property
        def __wrapped__(self) -> Callable[..., T]:
            return self._func

        @property
        def __cache__(self) -> dict[Any, T]:
            return self._cache

        def cache_clear(self) -> None:
            self._cache.clear()

        def cache_info(self) -> CacheInfo:
            return CacheInfo(self._hit, self._miss, len(self._cache))  # type: ignore # Pyright doesn't yet support attrs

    return decorator  # type: ignore


@cache
def cached_splitlines(s: str, strict: bool = False) -> list[str]:
    """
    A cached version of the `splitlines` method

    The strict flag controls whether a super set of universal newlines are deemed line boundaries.
    When strict is set to True, only '\n' line feed character is deemed line boundary.
    """

    if strict:
        return strict_splitlines(s)
    else:
        return s.splitlines()


@contextlib.contextmanager
def no_color_context() -> Iterator[None]:
    """
    Return a context manager. Within the context, the environment variable $NO_COLOR is set.
    Utilities supporting the NO_COLOR movement (https://no-color.org/) should automatically adjust their color output behavior.
    """

    orig_value = os.environ.get("NO_COLOR", None)
    os.environ["NO_COLOR"] = "true"

    try:
        yield
    finally:
        if orig_value is None:
            del os.environ["NO_COLOR"]
        else:
            os.environ["NO_COLOR"] = orig_value


def is_nan(x: Any) -> bool:
    """ Try best effort to detect NaN """

    # Alternative implementation is `is_nan = lambda x: x != x`

    if isinstance(x, Decimal):
        return x.is_nan()
    elif isinstance(x, Complex):
        return math.isnan(x.real) or math.isnan(x.imag)
    elif isinstance(x, Number):
        return math.isnan(x)  # type: ignore
    else:
        return False


def is_dtype(x: Any) -> bool:
    """ Determine if x is of type `numpy.dtype` """

    try:
        import numpy as np

        return isinstance(x, np.dtype)
    except ImportError:
        return False


def maxmin(*args, key=identityfunc, default=None):
    """ Mimic the builtin divmod() function """

    if len(args) <= 1:
        max_item = max(*args, key=key, default=default)
        min_item = min(*args, key=key, default=default)
    else:
        max_item = max(*args, key=key)
        min_item = min(*args, key=key)

    return max_item, min_item
