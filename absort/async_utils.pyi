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

_T = TypeVar("_T")
@overload
def run_async(
    func: Callable[..., Generator[_T, Any, Any]], *args: Any, **kwargs: Any
) -> AsyncGenerator[_T, Any]: ...
@overload
def run_async(
    func: Callable[..., Iterator[_T]], *args: Any, **kwargs: Any
) -> AsyncIterator[_T]: ...
@overload
def run_async(
    func: Callable[..., _T], *args: Any, **kwargs: Any
) -> Coroutine[Any, Any, _T]: ...
@overload
def asyncify(
    func: Callable[..., Generator[_T, Any, Any]]
) -> Callable[..., AsyncGenerator[_T, Any]]: ...
@overload
def asyncify(func: Callable[..., Iterator[_T]]) -> Callable[..., AsyncIterator[_T]]: ...
@overload
def asyncify(func: Callable[..., _T]) -> Callable[..., Coroutine[Any, Any, _T]]: ...
@overload
def run_in_event_loop(
    func: Callable[..., AsyncGenerator[_T, Any]]
) -> Callable[..., Generator[_T, Any, Any]]: ...
@overload
def run_in_event_loop(
    func: Callable[..., AsyncIterator[_T]]
) -> Callable[..., Iterator[_T]]: ...
@overload
def run_in_event_loop(
    func: Callable[..., Coroutine[Any, Any, _T]]
) -> Callable[..., _T]: ...
