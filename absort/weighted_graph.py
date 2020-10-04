from __future__ import annotations

from collections import defaultdict
from typing import Dict, DefaultDict, Set, Iterator, TypeVar


__all__ = ["WeightedGraph"]


#
# Thin semantic type annotation
#

# TODO: specify that Node type has to be hashable (constrained by current implementation,
# though we may consider to rewrite the implementation to waive the constraint in the future)
Node = TypeVar("Node")
Edge = Set[Node]
Weight = float
AdjacencyList = DefaultDict[Node, Set[Node]]


class WeightedGraph:
    def __init__(self) -> None:
        self._adjacency_list: AdjacencyList = defaultdict(set)
        self._weight_table: Dict[Edge, Weight] = {}

    __slots__ = ["_adjacency_list", "_weight_table"]

    def add_edge(self, v: Node, w: Node, weight: Weight) -> None:
        self._adjacency_list[v].add(w)
        self._adjacency_list[w].add(v)
        # FIXME set object is not hashable, hence not able to be used as dict key,
        # we should use frozenset instead.
        self._weight_table[{v, w}] = weight

    def remove_edge(self, v: Node, w: Node) -> None:
        self._adjacency_list[v].discard(w)
        self._adjacency_list[w].discard(v)
        self._weight_table.pop({v, w}, None)

    def copy(self) -> WeightedGraph:
        """ Note that this is NOT deep copy """

        new = WeightedGraph()

        new_adjacency_list: AdjacencyList = defaultdict(set)
        for node, nodes in self._adjacency_list:
            new_adjacency_list[node] = nodes.copy()
        new._adjacency_list = new_adjacency_list

        new._weight_table = self._weight_table.copy()
        return new

    def find_minimum_edge(self) -> Edge:
        try:
            edges = self._weight_table.keys()
            return min(edges, key=lambda edge: self._weight_table[edge])
        except ValueError:
            raise ValueError("No maximum edge in an empty or one-noded graph")

    def minimum_spanning_tree(self) -> Set[Node]:
        _graph = self.copy()
        seen: Set[Node] = set()

        minimum_edge = _graph.find_minimum_edge()
        seen.update(minimum_edge)
        _graph.remove_edge(*minimum_edge)

        while _graph._weight_table:
            candidate_edges = []
            for node in seen:
                candidate_edges.extend({node, w} for w in _graph._adjacency_list[node])
            target_edge = min(candidate_edges, key=lambda edge: _graph._weight_table[edge])
            seen.update(target_edge)
            _graph.remove_edge(*target_edge)

        return seen
