from collections.abc import Hashable

from hypothesis.strategies import from_type, frozensets, lists, recursive

from absort.utils import constantfunc


__all__ = ["anys", "hashables"]


anys = constantfunc(from_type(type))


# Reference: https://github.com/HypothesisWorks/hypothesis/issues/2324#issuecomment-573873111
def hashables(compound: bool = False) -> SearchStrategy[Hashable]:
    if compound:
        return recursive(
            from_type(Hashable), lambda x: frozensets(x) | lists(x).map(tuple)
        )
    else:
        return from_type(Hashable)
