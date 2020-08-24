from typing import TypeVar

__all__ = ["add_profile_decorator_to_class_methods"]


T = TypeVar("T")


def add_profile_decorator_to_class_methods(cls: T) -> T:
    """
    A dummy function. The actual function body will be injected by profile.py script at
    runtime.
    """
    return cls
