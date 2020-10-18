from hypothesis import given

from absort.utils import iequal
from absort.weighted_graph import WeightedGraph

from .strategies import graphs


# FIXME it's actually problematic to use the WeightedGraph itself to test itself.


def test_minimum_spanning_tree() -> None:
    g = WeightedGraph()
    assert list(g.minimum_spanning_tree()) == []

    g.add_edge("A", "B", 1)
    g.add_edge("A", "D", 3)
    g.add_edge("B", "D", 5)
    g.add_edge("E", "D", 1)
    g.add_edge("E", "B", 1)
    g.add_edge("C", "B", 6)
    g.add_edge("C", "F", 2)
    g.add_edge("E", "F", 4)
    g.add_edge("E", "C", 5)
    assert list(g.minimum_spanning_tree()) == ["A", "B", "E", "D", "F", "C"]

    g.clear()
    g.add_node("A")
    assert list(g.minimum_spanning_tree()) == ["A"]


@given(graphs(directed=False, connected=True))
def test_minimum_spanning_tree_porperty_based(graph: WeightedGraph) -> None:
    mst = list(graph.minimum_spanning_tree())
    nodes = list(graph.nodes())
    assert len(mst) == len(nodes)
    assert set(mst) == set(nodes)


@given(graphs(directed=False, connected=True))
def test_minimum_spanning_tree_deterministic(graph: WeightedGraph) -> None:
    assert iequal(
        graph.minimum_spanning_tree(), graph.minimum_spanning_tree(), strict=True
    )
