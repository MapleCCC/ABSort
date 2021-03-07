"""
This module contains implementaion of some clustering algorithms.
"""


import random
from collections import defaultdict
from collections.abc import Callable, Iterator
from itertools import combinations
from typing import TypeVar

from .weighted_graph import WeightedGraph


__all__ = ["chenyu"]


Point = TypeVar("Point")
Cluster = list[Point]


def chenyu(
    points: Cluster, distance: Callable[[Point, Point], float], k: int
) -> Iterator[Cluster]:
    """
    A derterministic divisive hierarchical clustering algorithm proposed by Chen Yu (https://github.com/vincentcheny)

    The output is a sequence of clusters (a cluster is a list of points), where consecutive clusters are closer.

    The k argument is an algorithmic parameter to tune. k has to be an integer larger than 1.
    Smaller k yields better clustering quality, while larger k yields less time complexity.

    The points argument accepts a list of point object. The point object is required to be hashable.

    The distance argument accepts a callable that returns the distance between two point objects.

    Assuming that the distance calculation cost is expensive and dominant over other costs,
    then the time complexity is k*n*(ln(n)/ln(k)-1) = O(n*ln(n)).
    """

    def rec_chenyu(points: Cluster) -> Iterator[Cluster]:
        if len(points) < k:
            yield points
            return

        centroids = r.sample(points, k)

        clusters: defaultdict[Point, Cluster] = defaultdict(list)
        for p in points:
            nearest_centroid = min(centroids, key=lambda x: distance(x, p))
            clusters[nearest_centroid].append(p)

        # If all points overlap
        if len(clusters) == 1:
            yield next(iter(clusters.values()))
            return

        graph: WeightedGraph[Point] = WeightedGraph()
        for c1, c2 in combinations(centroids, 2):
            weight = distance(c1, c2)
            graph.add_edge(c1, c2, weight)

        for centroid in graph.minimum_spanning_tree():
            cluster = clusters[centroid]
            yield from rec_chenyu(cluster)

    assert k >= 2, "k should be an integer larger than 1"

    r = random.Random(len(points))
    return rec_chenyu(points)
