from itertools import chain

from hypothesis import given
from hypothesis.strategies import booleans

from absort.directed_graph import DirectedGraph
from absort.utils import iequal

from .strategies import graphs


# TODO use hypothesis GhostWrite to create test of topological_sort against graphlib.TopologicalSorter

# FIXME it's actually problematic to use the DirectedGraph itself to test itself.


@given(graphs(acyclic=True), booleans())
def test_topological_sort_is_deterministic(graph: DirectedGraph, reverse: bool) -> None:
    assert iequal(
        graph.topological_sort(reverse=reverse),
        graph.topological_sort(reverse=reverse),
        strict=True,
    )


@given(graphs(acyclic=True), booleans())
def test_topological_sort(graph: DirectedGraph, reverse: bool) -> None:
    sorted_nodes = list(graph.topological_sort(reverse=reverse))
    nodes = list(graph.nodes())

    assert len(sorted_nodes) == len(nodes)
    assert set(sorted_nodes) == set(nodes)


@given(graphs())
def test_bfs_is_deterministic(graph: DirectedGraph) -> None:
    for node in graph.nodes():
        assert iequal(graph.bfs(node), graph.bfs(node), strict=True)


@given(graphs())
def test_dfs_is_deterministic(graph: DirectedGraph) -> None:
    for node in graph.nodes():
        assert iequal(graph.dfs(node), graph.dfs(node), strict=True)


@given(graphs())
def test_strongly_connected_components_is_deterministic(graph: DirectedGraph) -> None:
    assert iequal(
        graph.strongly_connected_components(),
        graph.strongly_connected_components(),
        strict=True,
    )


@given(graphs())
def test_strongly_connected_components(graph: DirectedGraph) -> None:
    sccs = graph.strongly_connected_components()
    scc_nodes = list(chain(*sccs))
    nodes = list(graph.nodes())

    assert len(scc_nodes) == len(nodes)
    assert set(scc_nodes) == set(nodes)
