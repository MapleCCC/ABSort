import contextlib
import difflib
import functools
import io
import math
import os
import sys
import tokenize
from collections import deque, namedtuple
from pathlib import Path
from typing import (
    IO,
    Any,
    Callable,
    Deque,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    TypeVar,
)

from colorama import Fore, Style

__all__ = [
    "ireverse",
    "xreverse",
    "beginswith",
    "bright_red",
    "bright_green",
    "bright_blue",
    "bright_yellow",
    "colored_unified_diff",
    "add_profile_decorator_to_class_methods",
    "cached_splitlines",
    "silent_context",
    "lru_cache_with_key",
    "detect_encoding",
    "apply",
    "first_true",
    "dirsize",
]

# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


def ireverse(iterable: Iterable) -> Iterable:
    """ Similar to the builtin function reversed(), except accept wider input """
    l = list(iterable)
    for i in range(len(l)):
        yield l[~i]


def xreverse(iterable: Iterable) -> List:
    """
    Similar to the builtin function reversed(), except accept wider input,
    and return non-lazy result
    """
    return list(iterable)[::-1]


def beginswith(s: str, prefix: str) -> bool:
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


T = TypeVar("T")


def add_profile_decorator_to_class_methods(cls: T) -> T:
    """
    A dummy function. The actual function body will be injected by profile.py script at
    runtime.
    """
    return cls


@functools.lru_cache
def cached_splitlines(s: str) -> List[str]:
    return s.splitlines()


@contextlib.contextmanager
def silent_context() -> Iterator:
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, "a")
    # sys.stderr = open(os.devnull, "a")
    try:
        yield
    finally:
        sys.stdout = original_stdout


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


def lru_cache_with_key(
    key: Callable, maxsize: Optional[int] = 128
) -> Callable[[Callable], Callable]:
    def lru_cache(fn: Callable) -> Callable:
        lru = LRU(maxsize=maxsize)
        CacheInfo = namedtuple("CacheInfo", ["hit", "miss", "maxsize", "currsize"])
        hit = miss = 0

        @functools.wraps(fn)
        @profile  # type: ignore
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            arg_key = key(*args, **kwargs)
            if arg_key in lru:
                nonlocal hit
                hit += 1
                return lru[arg_key]
            else:
                nonlocal miss
                miss += 1
                result = fn(*args, **kwargs)
                lru.update(arg_key, result)
                return result

        wrapper.__lru__ = lru  # type: ignore
        wrapper.cache_info = lambda: CacheInfo(hit, miss, maxsize, lru.size)  # type: ignore
        wrapper.clear_cache = lru.clear  # type: ignore

        return wrapper

    return lru_cache


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


def apply(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """ Equivalent to Haskell's $ function """
    return fn(*args, **kwargs)


def first_true(
    iterable: Iterable, *, default: Any = None, pred: Callable = None
) -> Any:
    if pred is None:
        pred = bool
    for elem in iterable:
        if pred(elem):
            return elem
    return default


def dirsize(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file)
