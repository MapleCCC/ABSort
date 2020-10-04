from typing import Callable, List, TypeVar

from .utils import constantfunc, lru_cache_with_key


__all__ = ["tree_distance"]


# TODO use collections.UserList to add new Forest type, instead of using Forest as a type alias of the List type

# TODO use more advanced algorithms to replace the classic Zhang-Shasha algorithm. E.g. RTED, PQ-Gram, AP-TED+, etc.

Tree = TypeVar("Tree")
Forest = List[Tree]
EmptyForest = []
contains_one_tree = lambda forest: len(forest) == 1


def tree_distance(
    tree1: Tree,
    tree2: Tree,
    children: Callable[[Tree], Forest] = None,
    insert_cost: Callable[[Tree], float] = None,
    delete_cost: Callable[[Tree], float] = None,
    rename_cost: Callable[[Tree, Tree], float] = None,
) -> float:
    """
    Implementation is Zhang-Shasha's tree edit distance algorithm.

    Reference: https://epubs.siam.org/doi/abs/10.1137/0218082

    Note that the rename_cost function **should** return 0 for identical nodes.
    """

    def remove_rightmost_root(forest: Forest) -> Forest:
        rightmost_tree = forest[-1]
        rightmost_tree_children = children(rightmost_tree)
        return forest[:-1] + rightmost_tree_children

    calculate_cache_key = lambda forest1, forest2: (
        tuple(map(id, forest1)),
        tuple(map(id, forest2)),
    )

    @lru_cache_with_key(key=calculate_cache_key, maxsize=None)
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

    if insert_cost is None:
        insert_cost = constantfunc(1)
    if delete_cost is None:
        delete_cost = constantfunc(1)
    if rename_cost is None:

        # hopefully a sane default
        def default_rename_cost(tree1: Tree, tree2: Tree) -> float:
            return int(tree1 != tree2)

        rename_cost = default_rename_cost

    return forest_distance([tree1], [tree2])
