import contextlib
import difflib
import functools
import os
import sys
from typing import Any, Iterable, Iterator, List, TypeVar

from colorama import Fore, Style

__all__ = [
    "reverse",
    "beginswith",
    "colored_unified_diff",
    "add_profile_decorator_to_class_methods",
    "cached_splitlines",
    "silent_context",
]

# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


def reverse(iterable: Iterable) -> Iterable:
    l = list(iterable)
    for i in range(len(l)):
        yield l[~i]


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
