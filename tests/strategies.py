"""
This module contains a collection of hypothesis strategies for convenient use.
"""

from collections.abc import Hashable, Sequence
from itertools import combinations, permutations
from typing import TypeVar, Union

from hypothesis.strategies import (
    SearchStrategy,
    composite,
    floats,
    from_type,
    frozensets,
    integers,
    lists,
    recursive,
    sampled_from,
)

from absort.directed_graph import DirectedGraph
from absort.utils import constantfunc, is_nan
from absort.weighted_graph import WeightedGraph


__all__ = ["anys", "hashables", "graphs"]


T = TypeVar("T")


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

        # Hypothesis doesn't generate numpy.dtype when numpy is not installed in the environment
        try:
            import numpy
        except ImportError:
            pass
        else:
            if isinstance(x, numpy.dtype):
                return False

        if is_nan(x):
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
            # TODO
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
        if acyclic:
            # TODO
            raise NotImplementedError

        if not connected:
            # TODO
            raise NotImplementedError

        node_pools = draw(lists(nodes(), unique=True))

        graph = WeightedGraph()
        if not len(node_pools):
            return graph
        for node in node_pools:
            graph.add_node(node)

        possible_edges = [{n1, n2} for n1, n2 in combinations(node_pools, 2)]

        edges = []
        spanning_tree, not_in_tree = node_pools[:1], node_pools[1:]
        for _ in range(len(node_pools) - 1):
            one_end = draw(sampled_from(spanning_tree))
            the_other_end = draw(sampled_from(not_in_tree))
            edge = {one_end, the_other_end}
            edges.append(edge)
            possible_edges.remove(edge)
            spanning_tree.append(the_other_end)
            not_in_tree.remove(the_other_end)

        n = len(possible_edges)
        if n:
            indices = draw(lists(integers(min_value=0, max_value=n - 1), unique=True))
        else:
            indices = []
        edges.extend(possible_edges[index] for index in indices)

        for edge in edges:
            weight = draw(floats())
            graph.add_edge(*edge, weight)

        return graph


@composite
def products(draw, *sequences: Sequence[T]) -> tuple[T, ...]:
    return tuple(draw(sampled_from(seq)) for seq in sequences)
