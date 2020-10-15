from collections import Counter, deque
from collections.abc import Callable, Hashable, Iterable
from itertools import repeat
from typing import TypeVar, Union

from .utils import (
    constantfunc,
    identityfunc,
    larger_recursion_limit,
    memoization,
    on_except_return,
)


__all__ = ["zhangshasha", "pqgram"]


# TODO use collections.UserList to add new Forest type, instead of using Forest as a type alias of the list type

# TODO use more advanced algorithms to replace the classic Zhang-Shasha algorithm. E.g. RTED, PQ-Gram, AP-TED+, etc.

Tree = TypeVar("Tree")
Forest = list[Tree]
EmptyForest: Forest = []
contains_one_tree: Callable[[Forest], bool] = lambda forest: len(forest) == 1


def zhangshasha(
    tree1: Tree,
    tree2: Tree,
    children: Callable[[Tree], Iterable[Tree]],
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
        rightmost_tree_children = list(children(rightmost_tree))
        return forest[:-1] + rightmost_tree_children

    calculate_cache_key = lambda forest1, forest2: (
        tuple(map(id, forest1)),
        tuple(map(id, forest2)),
    )

    @memoization(key=calculate_cache_key)
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
            candidates: list[float] = [None] * 3  # type: ignore

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
            candidates: list[float] = [None] * 3  # type: ignore

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

    with larger_recursion_limit():
        result = forest_distance([tree1], [tree2])

    return result


Label = TypeVar("Label")
LabelTuple = tuple[Label, ...]
Register = deque[Label]
Index = Counter[Union[int, LabelTuple]]

DUMMY_LABEL = object()


def pqgram(
    tree1: Tree,
    tree2: Tree,
    children: Callable[[Tree], Iterable[Tree]],
    p: int = 2,
    q: int = 3,
    label: Callable[[Tree], Label] = identityfunc,
) -> float:
    """
    Implementation of PQ-Gram tree distance algorithm.
    Reference: https://dl.acm.org/doi/abs/10.1145/1670243.1670247

    Additional details: the output is normalized pqgram distance, i.e. between 0 and 1.
    """

    assert p > 0 and q > 0

    index1 = pqgram_index(tree1, children, p, q, label, compact=True)
    index2 = pqgram_index(tree2, children, p, q, label, compact=True)

    symmetric_diff = sum(((index1 - index2) + (index2 - index1)).values())
    total = sum((index1 | index2).values())

    if not total:
        return 0
    return symmetric_diff / total


def pqgram_index_calculate_key(
    tree: Tree,
    children: Callable[[Tree], Iterable[Tree]],
    p: int,
    q: int,
    label: Callable[[Tree], Label],
) -> Hashable:
    return (id(tree), children, p, q, label)


@memoization(key=pqgram_index_calculate_key)
def pqgram_index(
    tree: Tree,
    children: Callable[[Tree], Iterable[Tree]],
    p: int = 2,
    q: int = 3,
    label: Callable[[Tree], Label] = identityfunc,
    compact: bool = False,
) -> Index:
    def construct_index_entry(stem: Register, base: Register) -> Union[int, LabelTuple]:
        label_tuple = (*stem, *base)

        if compact:
            # TODO possible micro-optimization: calculate tuple hash without actually constructing the tuple.
            return hash(label_tuple)
        else:
            return label_tuple

    def rec_pqgram_index(tree: Tree) -> None:
        base: Register = deque(repeat(DUMMY_LABEL, q), maxlen=q)
        stem.append(label(tree))

        children_count = 0
        for child in children(tree):
            base.append(label(child))
            entry = construct_index_entry(stem, base)
            index[entry] += 1
            rec_pqgram_index(child)
            children_count += 1

        if children_count:
            for _ in range(q - 1):
                base.append(DUMMY_LABEL)
                entry = construct_index_entry(stem, base)
                index[entry] += 1
        else:
            entry = construct_index_entry(stem, base)
            index[entry] += 1

    index: Index = Counter()
    stem: Register = deque(repeat(DUMMY_LABEL, p), maxlen=p)
    rec_pqgram_index(tree)
    return index
