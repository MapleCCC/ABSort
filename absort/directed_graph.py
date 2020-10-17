# TODO: replace with builtin implementation after functools.TopologicalSorter
# is added to public interface after Python3.9.

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable, Iterator
from typing import Generic, Optional, TypeVar

from more_itertools import first, ilen

from .collections_extra import OrderedSet
from .utils import identityfunc

#
# Thin semantic type abstraction
#

# TODO: specify that Node type has to be hashable (constrained by current implementation,
# though we may consider to rewrite the implementation to waive the constraint in the future)
Node = TypeVar("Node")
Edge = tuple[Node, Node]
AdjacencyList = defaultdict[Node, OrderedSet[Node]]


__all__ = ["CircularDependencyError", "SelfLoopError", "DirectedGraph"]


class CircularDependencyError(Exception):
    pass


class SelfLoopError(Exception):
    pass


# Graph is represented internally as data structure adjacency list
class DirectedGraph(Generic[Node]):
    def __init__(self) -> None:
        self._adjacency_list: AdjacencyList = defaultdict(OrderedSet)

    __slots__ = "_adjacency_list"

    def add_edge(self, v: Node, w: Node) -> None:
        if v == w:
            raise SelfLoopError("Self-pointing dependency is not accepted")

        self._adjacency_list[v].add(w)

        # Add w to adjacency list. This line is necessary because without it, some
        # nodes who are sinks of the graph (i.e., have zero out-going edge) would
        # not appear as keys in adjacency list.
        self._adjacency_list[w]

    def add_node(self, node: Node) -> None:
        self._adjacency_list[node]

    def __contains__(self, node: Node) -> bool:
        return node in self._adjacency_list

    def connected(self) -> bool:
        if not self._adjacency_list:
            return True

        entry = first(self._adjacency_list.keys())
        return ilen(self.bfs(entry)) == len(self._adjacency_list)

    def bfs(self, source: Node) -> Iterator[Node]:
        """
        Depending on the connectivity of the graph, it may not traverse all the nodes.
        For the same edge/node insertion order, the output is deterministic.
        """

        assert source in self._adjacency_list

        queue: deque[Node] = deque([source])
        traversed: set[Node] = set()

        while queue:
            node = queue.popleft()
            if node in traversed:
                continue
            yield node
            traversed.add(node)
            queue.extend(self._adjacency_list[node])

    def dfs(self, source: Node) -> Iterator[Node]:
        """
        Depending on the connectivity of the graph, it may not traverse all the nodes.
        For the same edge/node insertion order, the output is deterministic.
        """

        assert source in self._adjacency_list

        stack: list[Node] = [source]
        traversed: set[Node] = set()

        while stack:
            node = stack.pop()
            if node in traversed:
                continue
            yield node
            traversed.add(node)
            stack.extend(self._adjacency_list[node])

    def detect_back_edge(self, source: Node) -> Optional[Edge]:
        """
        Return one back edge, or None if no back edge is found.

        Note that depending on the connectivity of the graph, this method may not traverse
        all the nodes. So this method reporting no back edge found doesn't necessarily
        imply that there is not cycle in the graph.
        """

        assert source in self._adjacency_list

        stack: list[Node] = [source]
        current_path: list[Optional[Node]] = [None]

        while stack:
            node = stack[-1]

            if node != current_path[-1]:
                current_path.append(node)
                for child in self._adjacency_list[node]:
                    if child in current_path:
                        return (node, child)
                    stack.append(child)

            else:
                stack.pop()
                current_path.pop()

        return None

    def get_transpose_graph(self) -> DirectedGraph[Node]:
        new_graph: DirectedGraph[Node] = DirectedGraph()

        for key in self._adjacency_list.keys():
            new_graph._adjacency_list[key] = OrderedSet()

        for node, children in self._adjacency_list.items():
            for child in children:
                new_graph._adjacency_list[child].add(node)

        return new_graph

    def copy(self) -> DirectedGraph[Node]:
        """
        Note that this is shallow copy, NOT deep copy.

        The interface guarantees deep copy of the whole tree structure, but not to the
        level of Node internal. User are responsible to ensure deep copy of the Node
        internal.
        """

        new_graph: DirectedGraph[Node] = DirectedGraph()

        for node, children in self._adjacency_list.items():
            new_graph._adjacency_list[node] = children.copy()

        return new_graph

    def topological_sort(
        self,
        reverse: bool = False,
        same_rank_sorter: Callable[[list[Node]], list[Node]] = None,
    ) -> Iterator[Node]:
        """
        Note that `reversed(topological_sort)` is not equivalent to `topological_sort(reverse=True)`

        For the same edge/node insertion order, the output is deterministic.

        This method traverses all the nodes regardless of the connectivity of the graph.
        """

        def find_sources(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            sources: OrderedSet[Node] = OrderedSet(graph._adjacency_list.keys())

            for children in graph._adjacency_list.values():
                sources -= children

            if not sources and graph._adjacency_list:
                raise CircularDependencyError(
                    "Circular dependency detected! "
                    + "Try to run the method detect_back_edge() to find back edges."
                )

            return sources

        def find_sinks(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            sinks: OrderedSet[Node] = OrderedSet()

            for node, children in graph._adjacency_list.items():
                if not children:
                    sinks.add(node)

            if not sinks and graph._adjacency_list:
                raise CircularDependencyError(
                    "Circular dependency detected! "
                    + "Try to run the method detect_back_edge() to find back edges."
                )

            return sinks

        def remove_sources(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            srcs = find_sources(graph)

            for src in srcs:
                del graph._adjacency_list[src]

            for node in graph._adjacency_list:
                graph._adjacency_list[node] -= srcs

            return srcs

        def remove_sinks(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            sinks = find_sinks(graph)

            for sink in sinks:
                del graph._adjacency_list[sink]

            for node in graph._adjacency_list:
                graph._adjacency_list[node] -= sinks

            return sinks

        if same_rank_sorter is None:
            same_rank_sorter = identityfunc

        _graph = self.copy()

        if not reverse:
            while srcs := remove_sources(_graph):
                yield from same_rank_sorter(list(srcs))

        else:
            while sinks := remove_sinks(_graph):
                yield from same_rank_sorter(list(sinks))

    def relaxed_topological_sort(
        self,
        reverse: bool = False,
        same_rank_sorter: Callable[[list[Node]], list[Node]] = None,
    ) -> Iterator[Node]:
        """
        A more relaxed topological sort. When there are no more source/sink node left, treat
        all leftover nodes as the same rank.

        For the same edge/node insertion order, the output is deterministic.
        """

        def find_sources(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            sources: OrderedSet[Node] = OrderedSet(graph._adjacency_list.keys())

            for children in graph._adjacency_list.values():
                sources -= children

            if not sources and graph._adjacency_list:
                # Detected circular dependency
                # When there are no more source node left, treat all leftover nodes as
                # the same rank.
                return OrderedSet(graph._adjacency_list.keys())

            return sources

        def find_sinks(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            sinks: OrderedSet[Node] = OrderedSet()

            for node, children in graph._adjacency_list.items():
                if not children:
                    sinks.add(node)

            if not sinks and graph._adjacency_list:
                # Detected circular dependency
                # When there are no more sink node left, treat all leftover nodes as
                # the same rank.
                return OrderedSet(graph._adjacency_list.keys())

            return sinks

        def remove_sources(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            srcs = find_sources(graph)

            for src in srcs:
                del graph._adjacency_list[src]

            for node in graph._adjacency_list:
                graph._adjacency_list[node] -= srcs

            return srcs

        def remove_sinks(graph: DirectedGraph[Node]) -> OrderedSet[Node]:
            sinks = find_sinks(graph)

            for sink in sinks:
                del graph._adjacency_list[sink]

            for node in graph._adjacency_list:
                graph._adjacency_list[node] -= sinks

            return sinks

        if same_rank_sorter is None:
            same_rank_sorter = identityfunc

        _graph = self.copy()

        if not reverse:
            while srcs := remove_sources(_graph):
                yield from same_rank_sorter(list(srcs))
        else:
            while sinks := remove_sinks(_graph):
                yield from same_rank_sorter(list(sinks))

    def __str__(self) -> str:
        return "Graph({})".format(dict(self._adjacency_list))

    # TODO: ensure that eval(repr(x)) == x
    def __repr__(self) -> str:
        return self.__str__()


# TODO: move to unit test of Graph class
if __name__ == "__main__":
    g: DirectedGraph[str] = DirectedGraph()
    g.add_edge("0", "1")
    g.add_edge("1", "2")
    g.add_edge("0", "3")
    g.add_edge("3", "4")
    g.add_edge("1", "4")
    g.add_edge("4", "2")
    # g.add_edge("2", "0") Add this line to test case of cyclic graph
    print(g)
    print(list(g.bfs("0")))
    print(list(g.dfs("0")))
    print(list(g.topological_sort()))
