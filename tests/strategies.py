"""
This module contains a collection of hypothesis strategies for convenient use.
"""

from collections.abc import Hashable, Sequence as Seq
from itertools import combinations as std_combinations, permutations as std_permutations
from typing import TypeAlias, TypeVar

from hypothesis.strategies import (
    DrawFn,
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
from recipes.typing import vtuple

from absort.directed_graph import DirectedGraph
from absort.utils import is_dtype, is_nan
from absort.weighted_graph import WeightedGraph


__all__ = ["anys", "hashables", "graphs"]


T = TypeVar("T")


anys = from_type(type).flatmap(from_type)


# Reference: https://github.com/HypothesisWorks/hypothesis/issues/2324#issuecomment-573873111
def hashables(compound: bool = False) -> SearchStrategy[Hashable]:
    if compound:
        return recursive(
            from_type(Hashable), lambda x: frozensets(x) | lists(x).map(tuple)
        )
    else:
        return from_type(Hashable)


@composite
def products(draw: DrawFn, *seqs: Seq[T]) -> vtuple[T]:
    return tuple(draw(sampled_from(seq)) for seq in seqs)


# XXX can we pass in Iterable[T] instead of Seq[T]?
@composite
def permutations(draw: DrawFn, xs: Seq[T], n: int | None = None) -> list[T]:

    if not xs:
        return []

    if n is None:
        n = len(xs)

    indices = draw(lists(integers(0, len(xs) - 1), min_size=n, max_size=n, unique=True))
    return [xs[i] for i in indices]


# XXX is't correct to make combinations and permutations the same impl ?
combinations = permutations


Graph: TypeAlias = DirectedGraph | WeightedGraph


@composite
def graphs(
    draw, directed: bool = True, acyclic: bool = False, connected: bool = False
) -> Graph:
    """ Strategy to generate graphs """

    if directed:
        if connected:
            # TODO
            raise NotImplementedError

        nodes = draw(
            lists(
                hashables().filter(lambda x: not is_dtype(x) and not is_nan(x)),
                unique=True,
            )
        )

        if acyclic:
            edges = draw(lists(combinations(nodes, 2), unique=True))
        else:
            edges = draw(lists(permutations(nodes, 2), unique=True))

        graph = DirectedGraph()
        for node in nodes:
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

        nodes = draw(
            lists(
                hashables().filter(lambda x: not is_dtype(x) and not is_nan(x)),
                unique=True,
            )
        )

        graph = WeightedGraph()
        if not len(nodes):
            return graph
        for node in nodes:
            graph.add_node(node)

        possible_edges = [{n1, n2} for n1, n2 in std_combinations(nodes, 2)]

        edges = []
        spanning_tree, not_in_tree = nodes[:1], nodes[1:]
        for _ in range(len(nodes) - 1):
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
