from collections.abc import Hashable
from itertools import combinations

from hypothesis import given
from hypothesis.strategies import floats, from_type, integers, lists, one_of

from absort.directed_graph import DirectedGraph
from absort.utils import constantfunc, iequal


anys = constantfunc(from_type(type))
hashables = constantfunc(one_of(integers()))  # TODO


# TODO use hypothesis GhostWrite to create test of topological_sort against graphlib.TopologicalSorter

# TODO test on reverse=True
# TODO test on relaxed_topological_sort()


@given(lists(hashables(), unique=True), lists(integers(min_value=0), unique=True))
def test_topological_sort_is_deterministic(
    node_pool: list[Hashable], indices: list[int]
) -> None:
    possible_edges = list(combinations(node_pool, 2))

    if len(possible_edges):
        unique_indices = set(index % len(possible_edges) for index in indices)
    else:
        # Empty or one-noded graph
        unique_indices = []

    edges = [possible_edges[index] for index in unique_indices]

    graph1 = DirectedGraph()
    for edge in edges:
        graph1.add_edge(*edge)
    result1 = graph1.topological_sort()

    graph2 = DirectedGraph()
    for edge in edges:
        graph2.add_edge(*edge)
    result2 = graph2.topological_sort()

    assert iequal(result1, result2, strict=True)


@given(lists(hashables(), unique=True), lists(integers(min_value=0), unique=True))
def test_topological_sort_order(node_pool: list[Hashable], indices: list[int]) -> None:
    # No need to construct a connected graph, we only need to guarantee that it's acyclic.

    possible_edges = list(combinations(node_pool, 2))

    if len(possible_edges):
        unique_indices = set(index % len(possible_edges) for index in indices)  # type: ignore
    else:
        # Empty or one-noded graph
        unique_indices = []

    edges = [possible_edges[index] for index in unique_indices]

    graph = DirectedGraph()
    for edge in edges:
        graph.add_edge(*edge)
    nodes = list(graph.topological_sort())

    assert len(nodes) == len(node_pool)
    assert set(nodes) == set(node_pool)

    for u, v in edges:
        assert nodes.index(u) < nodes.index(v)
