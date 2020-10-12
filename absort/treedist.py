import sys
from typing import Callable, List, TypeVar

from .utils import constantfunc, lru_cache_with_key, on_except_return


__all__ = ["tree_edit_distance"]


# TODO use collections.UserList to add new Forest type, instead of using Forest as a type alias of the List type

# TODO use more advanced algorithms to replace the classic Zhang-Shasha algorithm. E.g. RTED, PQ-Gram, AP-TED+, etc.

Tree = TypeVar("Tree")
Forest = List[Tree]
EmptyForest: Forest = []
contains_one_tree: Callable[[Forest], bool] = lambda forest: len(forest) == 1


def tree_edit_distance(
    tree1: Tree,
    tree2: Tree,
    children: Callable[[Tree], Forest],
    insert_cost: Callable[[Tree], float] = constantfunc(1),
    delete_cost: Callable[[Tree], float] = constantfunc(1),
    rename_cost: Callable[[Tree, Tree], float] = lambda x, y: int(x != y),
) -> float:
    """
    Implementation is Zhang-Shasha's tree edit distance algorithm.

    Reference: https://epubs.siam.org/doi/abs/10.1137/0218082

    Note that the rename_cost function **should** return 0 for identical nodes.
    """

    def tree_size(tree: Tree) -> int:
        return 1 + sum(map(tree_size, children(tree)))

    def forest_size(forest: Forest) -> int:
        return sum(map(tree_size, forest))

    def remove_rightmost_root(forest: Forest) -> Forest:
        rightmost_tree = forest[-1]
        rightmost_tree_children = children(rightmost_tree)
        return forest[:-1] + rightmost_tree_children

    calculate_cache_key = lambda forest1, forest2: (
        tuple(map(id, forest1)),
        tuple(map(id, forest2)),
    )

    @lru_cache_with_key(key=calculate_cache_key, maxsize=None)
    @on_except_return(RecursionError, returns=0)
    def forest_distance(forest1: Forest, forest2: Forest) -> float:

        # Uncomment the following lines to activate debug mode
        #
        # from functools import partial
        # str_forest = (
        #     lambda forest: "["
        #     + ", ".join(map(partial(ast.dump, annotate_fields=False), forest))
        #     + "]"
        # )
        # print(f"Calling forest_distance({str_forest(forest1)}, {str_forest(forest2)})")

        if not forest1 and not forest2:
            return 0

        elif not forest1:
            new_forest2 = remove_rightmost_root(forest2)
            return forest_distance(forest1, new_forest2) + insert_cost(forest2[-1])

        elif not forest2:
            new_forest1 = remove_rightmost_root(forest1)
            return forest_distance(new_forest1, forest2) + delete_cost(forest1[-1])

        elif contains_one_tree(forest1) and contains_one_tree(forest2):
            new_forest1 = remove_rightmost_root(forest1)
            new_forest2 = remove_rightmost_root(forest2)
            candidates: List[float] = [None] * 3  # type: ignore

            candidates[0] = forest_distance(new_forest1, forest2) + delete_cost(
                forest1[-1]
            )
            candidates[1] = forest_distance(forest1, new_forest2) + insert_cost(
                forest2[-1]
            )
            candidates[2] = forest_distance(new_forest1, new_forest2) + rename_cost(
                forest1[-1], forest2[-1]
            )
            return min(candidates)

        else:
            new_forest1 = remove_rightmost_root(forest1)
            new_forest2 = remove_rightmost_root(forest2)
            candidates: List[float] = [None] * 3  # type: ignore

            candidates[0] = forest_distance(new_forest1, forest2) + delete_cost(
                forest1[-1]
            )
            candidates[1] = forest_distance(forest1, new_forest2) + insert_cost(
                forest2[-1]
            )
            candidates[2] = forest_distance(
                forest1[:-1], forest2[:-1]
            ) + forest_distance([forest1[-1]], [forest2[-1]])
            return min(candidates)

    orig_rec_limit = sys.getrecursionlimit()
    # 2147483647 is the largest integer that sys.setrecursionlimit() accepts in my development environment.
    # FIXME Does the Python language specification say anything about the largest number acceptable as argument to sys.setrecursionlimit()?
    sys.setrecursionlimit(2147483647)

    result = forest_distance([tree1], [tree2])

    sys.setrecursionlimit(orig_rec_limit)

    return result
