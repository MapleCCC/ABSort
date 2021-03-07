from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterator
from typing import Generic, TypeVar

from more_itertools import first

from .collections_extra import OrderedSet, UnionFind


__all__ = ["WeightedGraph"]


#
# Thin semantic type annotation
#

# Specify that Node type has to be hashable (constrained by current implementation, though we may consider to rewrite the implementation to waive the constraint in the future)
Node = TypeVar("Node", bound=Hashable)
Edge = frozenset[Node]
Weight = float
AdjacencyList = defaultdict[Node, OrderedSet[Node]]


class WeightedGraph(Generic[Node]):
    def __init__(self) -> None:
        self._adjacency_list = defaultdict(OrderedSet)  # type: AdjacencyList[Node]
        self._weight_table = {}  # type: dict[Edge[Node], Weight]

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

    def nodes(self) -> Iterator[Node]:
        yield from self._adjacency_list

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

    def find_minimum_edge(self) -> Edge[Node]:
        try:
            edges = self._weight_table
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

        edges = sorted(self._weight_table, key=self._weight_table.get)

        res = OrderedSet()
        uf = UnionFind(self._adjacency_list)
        cnt = 0
        for edge in edges:
            u, v = edge
            if uf.find(u) == uf.find(v):
                continue
            uf.union(u, v)
            res.update(edge)
            cnt += 1
            if cnt == len(self._adjacency_list) - 1:
                break

        if cnt < len(self._adjacency_list) - 1:
            raise ValueError("Unconnected graph has no minimum spanning tree")

        yield from res


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
