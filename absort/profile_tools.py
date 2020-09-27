from typing import Type

__all__ = ["add_profile_decorator_to_class_methods"]


# TODO how to use type annotation to specify that the input Type is same with the output Type?
def add_profile_decorator_to_class_methods(cls: Type) -> Type:
    """
    A dummy function. The actual function body will be injected by profile.py script at
    runtime.
    """
    return cls
