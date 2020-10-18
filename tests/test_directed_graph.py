from hypothesis import given
from hypothesis.strategies import booleans

from absort.directed_graph import DirectedGraph
from absort.utils import iequal

from .strategies import graphs


# TODO use hypothesis GhostWrite to create test of topological_sort against graphlib.TopologicalSorter


@given(graphs(acyclic=True), booleans())
def test_topological_sort_is_deterministic(graph: DirectedGraph, reverse: bool) -> None:
    assert iequal(
        graph.topological_sort(reverse=reverse),
        graph.topological_sort(reverse=reverse),
        strict=True,
    )


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
