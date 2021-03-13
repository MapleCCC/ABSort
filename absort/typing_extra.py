import ast
from abc import abstractmethod
from typing import Any, Protocol, TypeVar, Union


__all__ = [
    "Declaration",
    "DeclarationType",
    "Decoratable",
    "DecoratableType",
    "Comparable",
]


Declaration = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
DeclarationType = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]

Decoratable = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
DecoratableType = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


CT = TypeVar("CT", bound="Comparable")


class Comparable(Protocol):
    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        pass

    @abstractmethod
    def __lt__(self: CT, other: CT) -> bool:
        pass

    def __gt__(self: CT, other: CT) -> bool:
        return not self < other and not self == other

    def __le__(self: CT, other: CT) -> bool:
        return not self > other

    def __ge__(self: CT, other: CT) -> bool:
        return not self < other
