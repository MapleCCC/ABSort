# TODO: replace with builtin implementation after functools.TopologicalSorter
# is added to public interface after Python3.9.

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable, Hashable, Iterator, Sequence
from typing import Generic, Optional, TypeVar

from more_itertools import first, ilen
from recipes.misc import profile

from .collections_extra import OrderedSet
from .utils import identityfunc


#
# Thin semantic type abstraction
#

# Specify that Node type has to be hashable (constrained by current implementation, though we may consider to rewrite the implementation to waive the constraint in the future)
Node = TypeVar("Node", bound=Hashable)
Edge = tuple[Node, Node]
AdjacencyList = defaultdict[Node, OrderedSet[Node]]
SCC = Sequence[Node]  # strongly connected components


__all__ = ["CircularDependencyError", "SelfLoopError", "DirectedGraph"]


class CircularDependencyError(Exception):
    """ An exception to signal that circular dependency is detected """


class SelfLoopError(Exception):
    """ An exception to signal that self loop is detected """


# Graph is represented internally as data structure adjacency list
class DirectedGraph(Generic[Node]):
    def __init__(self) -> None:
        self._adjacency_list = defaultdict(OrderedSet)  # type: AdjacencyList[Node]

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

    def nodes(self) -> Iterator[Node]:
        yield from self._adjacency_list

    def connected(self) -> bool:
        if not self._adjacency_list:
            return True

        entry = first(self._adjacency_list)
        return ilen(self.bfs(entry)) == len(self._adjacency_list)

    def find_sources(self) -> OrderedSet[Node]:
        sources: OrderedSet[Node] = OrderedSet(self._adjacency_list)

        for children in self._adjacency_list.values():
            sources -= children

        return sources

    def find_sinks(self: DirectedGraph[Node]) -> OrderedSet[Node]:
        sinks: OrderedSet[Node] = OrderedSet()

        for node, children in self._adjacency_list.items():
            if not children:
                sinks.add(node)

        return sinks

    def bfs(self, source: Node) -> Iterator[Node]:
        """
        Depending on the connectivity of the graph, it may not traverse all the nodes.
        For the same edge/node insertion order, the output is deterministic.
        """

        assert source in self._adjacency_list

        queue = deque([source])  # type: deque[Node]
        traversed = set()  # type: set[Node]

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

    def detect_cycle(self) -> list[Node]:
        """
        Return a list of nodes which constitutes a cycle in the graph,
        or None if no cycle is found.

        Note that detect_cycle() is not intended to find all cycles in the graph.
        """

        nodes = set(self._adjacency_list)
        if not nodes:
            return []

        while nodes:
            path = []
            indexer = {}
            src = first(nodes)
            stack = [src]
            traversed = set()

            while stack:
                node = stack[-1]

                if node in traversed:
                    stack.pop()

                elif node != path[-1]:
                    path.append(node)
                    indexer[node] = len(path) - 1

                    for child in self._adjacency_list[node]:
                        if child in indexer:
                            # Found a cycle
                            return path[indexer[child] :] + [child]

                        stack.append(child)

                else:
                    path.pop()
                    del indexer[node]
                    stack.pop()
                    traversed.add(node)

            nodes -= traversed

        return []

    def detect_back_edge(self, source: Node) -> Optional[Edge[Node]]:
        """
        Return one back edge, or None if no back edge is found.

        Note that depending on the connectivity of the graph, this method may not traverse
        all the nodes. So this method reporting no back edge found doesn't necessarily
        imply that there is no cycle in the graph.
        """

        assert source in self._adjacency_list

        stack = [source]  # type: list[Node]
        current_path = [None]  # type: list[Optional[Node]]
        current_path_nodes = set()  # type: set[Node]
        traversed = set()  # type: set[Node]

        while stack:
            node = stack[-1]

            if node in traversed:
                stack.pop()

            elif node != current_path[-1]:
                current_path.append(node)
                current_path_nodes.add(node)

                for child in self._adjacency_list[node]:
                    if child in current_path_nodes:
                        # Found a back edge
                        return (node, child)

                    stack.append(child)

            else:
                stack.pop()
                current_path.pop()
                current_path_nodes.remove(node)
                traversed.add(node)

        return None

    def get_transpose_graph(self) -> DirectedGraph[Node]:
        new_graph: DirectedGraph[Node] = DirectedGraph()

        for node in self._adjacency_list:
            # This line is necessary, such that nodes with in-degree are also included in the new graph.
            new_graph._adjacency_list[node] = OrderedSet()

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

        if same_rank_sorter is None:
            same_rank_sorter = identityfunc

        if reverse:
            yield from self.get_transpose_graph().topological_sort()
            return

        indegree_table = defaultdict(int)
        for children in self._adjacency_list.values():
            for child in children:
                indegree_table[child] += 1

        cnt = 0
        sources = [node for node in self._adjacency_list if indegree_table[node] == 0]

        while sources:
            cnt += len(sources)
            yield from same_rank_sorter(sources)

            new_sources = []  # type: list[Node]
            for node in sources:
                for child in self._adjacency_list[node]:
                    indegree_table[child] -= 1

                    if indegree_table[child] == 0:
                        new_sources.append(child)

            sources = new_sources

        if cnt < len(self._adjacency_list):
            raise CircularDependencyError(
                "Circular dependency detected! "
                + "Try to run the method detect_cycle() to find cycle, "
                + "or detect_back_edge() to find back edges."
            )

    @profile
    def strongly_connected_components(self) -> Iterator[SCC[Node]]:
        """
        Find all strongly connected components.

        The implementation is Tarjan's algorithm, with linear time complexity O(|V|+|E|).

        It fallbacks to topological sort for a DAG.

        The output order is the reverse topological sort of the DAG formed by the SCCs.

        For the same edge/node insertion order, the output is deterministic.

        This method traverses all the nodes regardless of the connectivity of the graph.
        """

        @profile
        def rec_scc(node: Node) -> Iterator[SCC[Node]]:
            nonlocal count, stack

            indexer[node] = count
            lowlinks[node] = count
            count += 1
            stack.append(node)

            for child in self._adjacency_list[node]:
                if child not in indexer:
                    yield from rec_scc(child)
                    lowlinks[node] = min(lowlinks[node], lowlinks[child])

                elif child in stack:
                    lowlinks[node] = min(lowlinks[node], indexer[child])

            if lowlinks[node] == indexer[node]:
                stack, scc = stack[: stack.index(node)], stack[stack.index(node) :]
                yield scc

        count = 0
        stack: list[Node] = []
        indexer: dict[Node, int] = {}
        lowlinks: dict[Node, int] = {}

        for node in self._adjacency_list:
            if node not in indexer:
                yield from rec_scc(node)

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
    print(list(g.strongly_connected_components()))
