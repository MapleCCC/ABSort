from __future__ import annotations

import pickle
from collections import defaultdict
from collections.abc import Iterator
from hashlib import md5
from typing import Generic, TypeVar

from more_itertools import first

from .collections_extra import OrderedSet


__all__ = ["WeightedGraph"]


#
# Thin semantic type annotation
#

# TODO: specify that Node type has to be hashable (constrained by current implementation,
# though we may consider to rewrite the implementation to waive the constraint in the future)
Node = TypeVar("Node")
Edge = frozenset[Node]
Weight = float
AdjacencyList = defaultdict[Node, OrderedSet[Node]]


class WeightedGraph(Generic[Node]):
    def __init__(self) -> None:
        self._adjacency_list: AdjacencyList = defaultdict(OrderedSet)
        self._weight_table: dict[Edge, Weight] = {}

    __slots__ = ["_adjacency_list", "_weight_table"]

    def add_node(self, v: Node) -> None:
        self._adjacency_list[v]

    def add_edge(self, v: Node, w: Node, weight: Weight) -> None:
        if v == w:
            raise ValueError("Self loop is not supported")

        self._adjacency_list[v].add(w)
        self._adjacency_list[w].add(v)

        edge = frozenset({v, w})
        self._weight_table[edge] = weight

    def remove_edge(self, v: Node, w: Node) -> None:
        self._adjacency_list[v].discard(w)
        self._adjacency_list[w].discard(v)

        edge = frozenset({v, w})
        self._weight_table.pop(edge, None)

    @property
    def num_nodes(self) -> int:
        return len(self._adjacency_list)

    @property
    def num_edges(self) -> int:
        return len(self._weight_table)

    def weight(self, v: Node, w: Node) -> Weight:
        try:
            edge = frozenset({v, w})
            return self._weight_table[edge]

        except KeyError:
            raise ValueError(f"{{{v}, {w}}} is not an edge in the graph")

    def clear(self) -> None:
        self._adjacency_list.clear()
        self._weight_table.clear()

    def copy(self) -> WeightedGraph[Node]:
        """
        Note that this is shallow copy, NOT deep copy.

        The interface guarantees deep copy of the whole tree structure, but not to the
        level of Node internal. User are responsible to ensure deep copy of the Node
        internal.
        """

        new: WeightedGraph[Node] = WeightedGraph()

        for node, neighbors in self._adjacency_list.items():
            new._adjacency_list[node] = neighbors.copy()

        new._weight_table = self._weight_table.copy()

        return new

    def find_minimum_edge(self) -> Edge:
        try:
            edges = self._weight_table.keys()
            return min(edges, key=lambda edge: self._weight_table[edge])

        except ValueError:
            raise ValueError("No minimum edge in an empty or one-noded graph")

    def minimum_spanning_tree(self) -> Iterator[Node]:
        """
        For the same edge/node insertion order, output is guaranteed to be deterministic.

        The output is ordered in such a way that, except the first one, the smallest candidate edge is always greedily picked first.

        For disconnected graph, ValueError is raised.

        Every connected graph has a minimum spanning tree. (may not be unique)
        """

        if self.num_nodes == 0:
            return

        _graph = self.copy()
        seen: OrderedSet[Node] = OrderedSet()

        seen.add(first(_graph._adjacency_list.keys()))

        while len(seen) < _graph.num_nodes:
            candidate_edges = []

            for node in seen:
                for neighbor in _graph._adjacency_list[node]:
                    if neighbor not in seen:
                        edge = frozenset({node, neighbor})
                        candidate_edges.append(edge)

            target_edge = min(
                candidate_edges, key=lambda edge: _graph._weight_table[edge]
            )
            seen.update(target_edge)
            _graph.remove_edge(*target_edge)

        if len(seen) < len(self._adjacency_list):
            raise ValueError("Disconnected graph doesn't have minimum spanning tree")

        yield from seen


if __name__ == "__main__":
    g: WeightedGraph[str] = WeightedGraph()
    g.add_edge("A", "B", 1)
    g.add_edge("A", "D", 3)
    g.add_edge("B", "D", 5)
    g.add_edge("E", "D", 1)
    g.add_edge("E", "B", 1)
    g.add_edge("C", "B", 6)
    g.add_edge("C", "F", 2)
    g.add_edge("E", "F", 4)
    g.add_edge("E", "C", 5)
    print(list(g.minimum_spanning_tree()))
