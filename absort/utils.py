import contextlib
import difflib
import functools
import io
import itertools
import os
import sys
import tokenize
from collections import namedtuple
from functools import partial
from pathlib import Path
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
    "detect_encoding",
    "apply",
    "first_true",
    "dirsize",
    "rmdir",
    "Logger",
    "concat",
    "SingleThreadPoolExecutor",
    "compose",
    "whitespace_lines",
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


# The source code of open_with_encoding() is taken from autopep8 (https://github.com/hhatto/autopep8)
def open_with_encoding(
    filename: str, mode: str = "r", encoding: str = None, limit_byte_check: int = -1
) -> IO:
    """Return opened file with a specific encoding."""
    if not encoding:
        encoding = detect_encoding(filename, limit_byte_check=limit_byte_check)

    return io.open(
        filename, mode=mode, encoding=encoding, newline=""
    )  # Preserve line endings


# The source code of detect_encoding() is taken from autopep8 (https://github.com/hhatto/autopep8)
def detect_encoding(filename: str, limit_byte_check: int = -1) -> str:
    """Return file encoding."""
    try:
        with open(filename, "rb") as input_file:
            encoding = tokenize.detect_encoding(input_file.readline)[0]

        with open_with_encoding(filename, encoding=encoding) as test_file:
            test_file.read(limit_byte_check)

        return encoding
    except (LookupError, SyntaxError, UnicodeDecodeError):
        return "latin-1"


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


def dirsize(path: Path) -> int:
    """ Return the total size of a directory, in bytes """
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file)


def rmdir(path: Path) -> None:
    """ Remove a directory, also removing files and subdirectories inside. """

    if path.is_dir():
        raise NotADirectoryError(f"{path} is not a directory")

    for file in path.rglob("*.bak"):
        file.unlink()

    path.rmdir()


class Logger:
    """
    A lightweight logger.

    It's just a thin wrapper over the builtin print function, except that it prints
    strings with order numbers prepended.
    """

    def __init__(self) -> None:
        self._count = 1

    __slots__ = "_count"

    def log(self, s: str) -> None:
        """
        It's just a thin wrapper over the builtin print function, except that it prints
        strings with order numbers prepended.
        """
        print(bright_green(str(self._count) + ". ") + s)
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
