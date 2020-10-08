from typing import Callable, Type

from .utils import identityfunc


__all__ = ["add_profile_decorator_to_class_methods"]


# TODO how to use type annotation to specify that the input Type is same with the output Type?

# A dummy function. The actual function body will be injected by profile.py script at runtime.
add_profile_decorator_to_class_methods: Callable[[Type], Type] = identityfunc
