import ast
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, TypeVar


__all__ = [
    "Declaration",
    "Decoratable",
    "Comparable",
]

# FIXME a proper appraoch here is to use `sum type` feature to properly type this case.
# Reference: "Support for sealed classes" - https://mail.python.org/archives/list/typing-sig@python.org/thread/AKXUBJUUHBBKTLNIAFCA6HII5QQA2WFX/


if TYPE_CHECKING:
    Declaration = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
else:
    Declaration = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

Decoratable = Declaration


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
