from collections.abc import Callable
from typing import TypeVar


__all__ = ["add_profile_decorator_to_class_methods"]


T = TypeVar("T")

# Duplicate the definition of utils.identityfunc() here, to workaround circular imports
def identityfunc(input: T) -> T:
    """ An identity function """
    return input


# TODO how to use type annotation to specify that the input Type is same with the output Type?

# A dummy function. The actual function body will be injected by profile.py script at runtime.
add_profile_decorator_to_class_methods: Callable[[type], type] = identityfunc
