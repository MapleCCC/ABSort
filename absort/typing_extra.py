from abc import abstractmethod
from typing import Any, Protocol, TypeAlias, TypeVar


__all__ = ["PyVersion", "Comparable"]


CT = TypeVar("CT", bound="Comparable")


PyVersion: TypeAlias = tuple[int, int]


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
