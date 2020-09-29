import asyncio
import functools
import inspect
from functools import partial
from typing import Callable
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Callable,
    Coroutine,
    Generator,
    Iterator,
    TypeVar,
    overload,
)


__all__ = ["asyncify", "run_in_event_loop"]


_T = TypeVar("_T")


@overload
def asyncify(
    func: Callable[..., Generator[_T, Any, Any]]
) -> Callable[..., AsyncGenerator[_T, Any]]:
    ...


@overload
def asyncify(func: Callable[..., Iterator[_T]]) -> Callable[..., AsyncIterator[_T]]:
    ...


@overload
def asyncify(func: Callable[..., _T]) -> Callable[..., Coroutine[Any, Any, _T]]:
    ...


def asyncify(func: Callable) -> Callable:
    """
    A wrapper to delegate the function job to thread pool, i.e., non-blocking.
    """

    if inspect.isgeneratorfunction(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            pfunc = partial(list, func(*args, **kwargs))
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, pfunc)
            for result in results:
                yield result

        return wrapper

    elif inspect.isfunction(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            pfunc = partial(func, *args, **kwargs)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, pfunc)

        return wrapper

    else:
        raise ValueError


@overload
def run_in_event_loop(
    func: Callable[..., AsyncGenerator[_T, Any]]
) -> Callable[..., Generator[_T, Any, Any]]:
    ...


@overload
def run_in_event_loop(
    func: Callable[..., AsyncIterator[_T]]
) -> Callable[..., Iterator[_T]]:
    ...


@overload
def run_in_event_loop(
    func: Callable[..., Coroutine[Any, Any, _T]]
) -> Callable[..., _T]:
    ...


def run_in_event_loop(func: Callable) -> Callable:
    """
    A decorator to make coroutine function or asynchronous generator function run in event loop.
    """

    if inspect.isasyncgenfunction(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            async def entry():
                result = []
                async for value in func(*args, **kwargs):
                    result.append(value)
                return result

            yield from asyncio.run(entry())

        return wrapper

    elif inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return asyncio.run(func(*args, **kwargs))

        return wrapper

    else:
        raise ValueError
