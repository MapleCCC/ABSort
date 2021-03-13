import asyncio
import functools
import inspect
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from functools import partial
from typing import Any, NoReturn, TypeVar

from .utils import dispatch


__all__ = ["run_async", "asyncify", "run_in_event_loop"]


# FIXME In view of that the tedious and heavy type annotations in this module are visually
# bad and undermine the readability, should we just move the heavy and detailed type
# annotations to standalone type stub files, while only leaving some lightweight type
# annotations here?


T = TypeVar("T")


def run_async(func: Callable, *args, **kwargs):
    return asyncify(func)(*args, **kwargs)


@dispatch
def asyncify(func: Any) -> NoReturn:
    """
    A wrapper to delegate the function job to thread pool, i.e., non-blocking.

    Can be used as a decorator.
    """

    raise ValueError(f"Expect callable, got {type(func)}")


@asyncify.register(inspect.isgeneratorfunction)
def _(
    func: Callable[..., Generator[T, Any, Any]]
) -> Callable[..., AsyncGenerator[T, Any]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> AsyncGenerator[T, Any]:

        pfunc = partial(list, func(*args, **kwargs))
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, pfunc)
        for result in results:
            yield result

    return wrapper


@asyncify.register(inspect.ismethod)
@asyncify.register(inspect.isfunction)
def _(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:

        pfunc = partial(func, *args, **kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, pfunc)

    return wrapper


@dispatch
def run_in_event_loop(func: Any) -> NoReturn:
    """
    A decorator to make coroutine function or asynchronous generator function run in event loop.
    """

    raise ValueError(f"Expect callable, got {type(func)}")


@run_in_event_loop.register(inspect.isasyncgenfunction)
def _(
    func: Callable[..., AsyncGenerator[T, Any]]
) -> Callable[..., Generator[T, Any, Any]]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Generator[T, Any, Any]:
        async def entry() -> list[T]:

            result = []
            async for value in func(*args, **kwargs):
                result.append(value)
            return result

        yield from asyncio.run(entry())

    return wrapper


@run_in_event_loop.register(inspect.iscoroutinefunction)
def _(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:

        return asyncio.run(func(*args, **kwargs))

    return wrapper
