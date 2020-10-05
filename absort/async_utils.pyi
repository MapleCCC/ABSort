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

T = TypeVar("T")
@overload
def run_async(
    func: Callable[..., Generator[T, Any, Any]], *args: Any, **kwargs: Any
) -> AsyncGenerator[T, Any]: ...
@overload
def run_async(
    func: Callable[..., Iterator[T]], *args: Any, **kwargs: Any
) -> AsyncIterator[T]: ...
@overload
def run_async(
    func: Callable[..., T], *args: Any, **kwargs: Any
) -> Coroutine[Any, Any, T]: ...
@overload
def asyncify(
    func: Callable[..., Generator[T, Any, Any]]
) -> Callable[..., AsyncGenerator[T, Any]]: ...
@overload
def asyncify(func: Callable[..., Iterator[T]]) -> Callable[..., AsyncIterator[T]]: ...
@overload
def asyncify(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]: ...
@overload
def run_in_event_loop(
    func: Callable[..., AsyncGenerator[T, Any]]
) -> Callable[..., Generator[T, Any, Any]]: ...
@overload
def run_in_event_loop(
    func: Callable[..., AsyncIterator[T]]
) -> Callable[..., Iterator[T]]: ...
@overload
def run_in_event_loop(
    func: Callable[..., Coroutine[Any, Any, T]]
) -> Callable[..., T]: ...
