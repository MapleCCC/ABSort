import contextlib
import difflib
import functools
import math
import operator
import os
import sys
from collections import Counter, OrderedDict
from collections.abc import Callable, Collection, Hashable, Iterable, Iterator
from decimal import Decimal
from functools import cache
from itertools import combinations, zip_longest
from numbers import Complex, Number
from typing import IO, Any, Generic, TypeVar

import attrs
from more_itertools import UnequalIterablesError, zip_equal
from recipes.exceptions import Unreachable
from recipes.misc import bright_green, bright_red


__all__ = [
    "ireverse",
    "xreverse",
    "colorized_unified_diff",
    "cached_splitlines",
    "silent_context",
    "Logger",
    "is_blank_line",
    "is_blank_lines",
    "is_comment_line",
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

# TODO use more_itertools library's recipes to replace some functions here.


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


def colorized_unified_diff(
    a: list[str], b: list[str], *args: Any, **kwargs: Any
) -> Iterator[str]:
    """ Return unified diff view between a and b, with color """

    # for line in difflib.ndiff(a, b, *args, **kwargs):
    # for line in difflib.context_diff(a, b, *args, **kwargs):
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


def is_blank_line(line: str) -> bool:
    return not line.strip()


def is_blank_lines(lines: list[str]) -> bool:
    """ Return whether lines are all whitespaces """
    return all(is_blank_line(line) for line in lines)


def is_comment_line(line: str) -> bool:
    return line.lstrip().startswith("#")


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


def duplicated(elems: Iterable) -> bool:
    """ Detect duplicate elements """

    elems = list(elems)

    try:
        return len(set(elems)) < len(elems)

    except TypeError:
        # Elements are unhashable.
        # O(n**2) worst-case time complexity.
        seen = []
        for elem in elems:
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


def strict_splitlines(s: str, keepends: bool = False) -> list[str]:
    """
    Similar to the str.splitlines() function, except that the line boundaries are NOT a
    superset of universal newlines.
    """

    # Some edge cases handling is necessary to be as closed to the behavior of str.splitlines() as possible

    if not s:
        return []

    lines = s.split("\n")

    if lines[-1] == "":
        lines.pop()

    if keepends:
        for i in range(len(lines) - 1):
            lines[i] += "\n"
        if s[-1] == "\n":
            lines[-1] += "\n"
        return lines
    else:
        return lines


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
        # XXX Depend on whether partial-equalable, equalable, commutativity, transxxxx, etc.
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

    @attrs.define
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
            return CacheInfo(self._hit, self._miss, len(self._cache))

    return decorator  # type: ignore


@cache
def cached_splitlines(s: str, strict: bool = False) -> list[str]:
    """
    A cached version of the `splitlines` method

    The strict flag controls whether a super set of universal newlines are deemed line boundaries.
    When strict is set to True, only '\n' line feed character is deemed line boundary.
    """

    # XXX the `linecache` stdlib module

    if strict:
        return strict_splitlines(s)
    else:
        return s.splitlines()


@contextlib.contextmanager
def no_color_context() -> Iterator[None]:
    """
    Return a context manager. Within the context, the environment variable $NO_COLOR is
    set. Utilities supporting the NO_COLOR movement (https://no-color.org/) should
    automatically adjust their color output behavior.
    """

    orig_value = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "true"

    try:
        yield
    finally:
        # TODO how to elegantly unify these two cases.
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

    if not args:
        raise TypeError("maxmin expected at least 1 argument, got 0")

    seq = args[0] if len(args) == 1 else args

    curr_max = default
    curr_min = default

    for elem in seq:
        elem_key = key(elem)
        if elem_key > key(curr_max):
            curr_max = elem
        elif elem_key < key(curr_min):
            curr_min = elem

    return curr_max, curr_min


def char_diff(text1: str, text2: str) -> Counter[str]:

    # TODO purely functional multiset. persistent counter. persistent/frozen/immutable
    # map/dict. Take inspiration from clojure's builtin functions naming.

    # NOTE be careful that arithmetic operations between Counters could lead to
    # inadvertent removal of entries with non-positive counts. The only reliable way to
    # introduce negative counts is to use the `Counter.subtract()` method.

    c1 = Counter(text1)
    c2 = Counter(text2)
    a = c1 - c2
    b = c2 - c1
    b.subtract(a)
    return b
