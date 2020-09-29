import asyncio
import functools
import inspect
from functools import partial
from typing import Callable


__all__ = ["asyncify", "run_in_event_loop"]


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

    elif inspect.isfunction(func) or inspect.ismethod(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            pfunc = partial(func, *args, **kwargs)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, pfunc)

        return wrapper

    else:
        raise ValueError(f"Expect callable, got {type(func)}")


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
        raise ValueError(f"Expect callable, got {type(func)}")
