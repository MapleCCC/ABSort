# TODO: replace with builtin implementation after functools.TopologicalSorter
# is added to public interface after Python3.9.

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

# Thin semantic type abstraction
Node = Any
Edge = Tuple[Node, Node]
AdjacencyList = Dict[Node, Set[Node]]


__all__ = ["CircularDependencyError", "Graph"]


class CircularDependencyError(Exception):
    pass


# Graph is represented internally as data structure adjacency list
class Graph:
    def __init__(self) -> None:
        self._adjacency_list: AdjacencyList = defaultdict(set)

    __slots__ = "_adjacency_list"

    def add_edge(self, v: Node, w: Node) -> None:
        if v == w:
            raise CircularDependencyError("Self-pointing dependency is not accepted")
        self._adjacency_list[v].add(w)
        # add w to adjacency list. This line is necessary because without it, some
        # nodes who are sinks of the graph (i.e., have zero out-going edge) would
        # not appear as keys in adjacency list.
        self._adjacency_list[w]

    def add_node(self, node: Node) -> None:
        self._adjacency_list[node]

    def __contains__(self, node: Node) -> bool:
        return node in self._adjacency_list

    def bfs(self, source: Node) -> Iterator[Node]:
        assert source in self._adjacency_list
        queue = deque([source])
        traversed = set()
        while queue:
            node = queue.popleft()
            if node in traversed:
                continue
            yield node
            traversed.add(node)
            queue.extend(self._adjacency_list[node])

    # Optionally, we can implement dfs in iterative manner instead of recursive manner.
    # The main difference is whether user-maintained stack or runtime stack is
    # used to track information.
    def dfs(self, source: Node) -> Iterator[Node]:
        traversed: Set[Node] = set()
        yield from self._dfs(source, traversed)

    def _dfs(self, node: Node, traversed: Set[Node]) -> Iterator[Node]:
        assert node in self._adjacency_list
        if node in traversed:
            return
        yield node
        traversed.add(node)
        for child in self._adjacency_list[node]:
            yield from self._dfs(child, traversed)

    def detect_back_edge(self, source: Node) -> Optional[Edge]:
        assert source in self._adjacency_list
        stack = [source]
        current_path: List[Optional[Node]] = [None]
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

    def get_invert_graph(self) -> Graph:
        new_adjlist: AdjacencyList = dict()
        for key in self._adjacency_list.keys():
            new_adjlist[key] = set()
        for node, children in self._adjacency_list.items():
            for child in children:
                new_adjlist[child].add(node)

        new_graph = Graph()
        new_graph._adjacency_list = new_adjlist
        return new_graph

    def copy(self) -> Graph:
        # Deep copy
        new_adjlist = dict()
        for node, children in self._adjacency_list.items():
            new_adjlist[node] = children.copy()
        new_graph = Graph()
        new_graph._adjacency_list = new_adjlist
        return new_graph

    def topological_sort(self) -> Iterator[Node]:
        def find_sources(graph: Graph) -> Set[Node]:
            adjlist = graph._adjacency_list
            sources = set(adjlist.keys())
            for children in adjlist.values():
                sources -= children
            if not sources and adjlist:
                raise CircularDependencyError(
                    "Circular dependency detected! "
                    + "Try to run the method detect_back_edge() to find back edges."
                )
            return sources

        def remove_sources(graph: Graph) -> Set[Node]:
            srcs = find_sources(graph)
            for src in srcs:
                del graph._adjacency_list[src]
            for node in graph._adjacency_list:
                graph._adjacency_list[node] -= srcs
            return srcs

        _graph = self.copy()
        while srcs := remove_sources(_graph):
            yield from srcs

    def __str__(self) -> str:
        return "Graph({})".format(dict(self._adjacency_list))

    # TODO: ensure that eval(repr(x)) == x
    def __repr__(self) -> str:
        return self.__str__()


# TODO: move to unit test of Graph class
if __name__ == "__main__":
    g = Graph()
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
