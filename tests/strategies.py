import math
from collections.abc import Hashable
from decimal import Decimal
from itertools import combinations, permutations
from numbers import Complex, Number
from typing import Union

from hypothesis.strategies import (
    SearchStrategy,
    composite,
    from_type,
    frozensets,
    integers,
    lists,
    recursive,
)

from absort.directed_graph import DirectedGraph
from absort.utils import constantfunc
from absort.weighted_graph import WeightedGraph


__all__ = ["anys", "hashables", "graphs"]


anys = constantfunc(from_type(type))


# Reference: https://github.com/HypothesisWorks/hypothesis/issues/2324#issuecomment-573873111
def hashables(compound: bool = False) -> SearchStrategy[Hashable]:
    if compound:
        return recursive(
            from_type(Hashable), lambda x: frozensets(x) | lists(x).map(tuple)
        )
    else:
        return from_type(Hashable)


def nodes() -> SearchStrategy:
    def filter_func(x):
        import numpy

        if isinstance(x, Decimal):
            return not x.is_nan()
        elif isinstance(x, Complex):
            return not math.isnan(x.real) and not math.isnan(x.imag)
        elif isinstance(x, Number):
            return not math.isnan(x)
        elif isinstance(x, numpy.dtype):
            return False
        return True

    return hashables().filter(filter_func)


Graph = Union[DirectedGraph, WeightedGraph]


@composite
def graphs(
    draw, directed: bool = True, acyclic: bool = False, connected: bool = False
) -> Graph:
    if directed:
        if connected:
            raise NotImplementedError

        node_pools = draw(lists(nodes(), unique=True))

        if acyclic:
            possible_edges = list(combinations(node_pools, 2))
        else:
            possible_edges = list(permutations(node_pools, 2))

        n = len(possible_edges)
        if n:
            indices = draw(lists(integers(min_value=0, max_value=n - 1), unique=True))
        else:
            # Empty or one-noded graph
            indices = []

        edges = [possible_edges[index] for index in indices]

        graph = DirectedGraph()
        for node in node_pools:
            graph.add_node(node)
        for edge in edges:
            graph.add_edge(*edge)

        return graph

    else:
        raise NotImplementedError
