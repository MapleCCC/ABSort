from absort.weighted_graph import WeightedGraph


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
    assert list(g.minimum_spanning_tree()) == ["B", "A", "E", "D", "F", "C"]

    g.clear()
    g.add_node("A")
    assert list(g.minimum_spanning_tree()) == ["A"]
