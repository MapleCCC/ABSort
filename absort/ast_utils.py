import ast
import copy
from collections import deque
from typing import Callable, Deque, Iterator, List, Optional, Set

from .treedist import tree_distance
from .utils import (
    beginswith,
    cached_splitlines,
    compose,
    hamming_distance,
    ireverse,
    lfu_cache_with_key,
)


__all__ = [
    "ast_pretty_dump",
    "ast_ordered_walk",
    "ast_strip_location_info",
    "ast_get_leading_comment_and_decorator_list_source_lines",
    "ast_get_leading_comment_source_lines",
    "ast_get_decorator_list_source_lines",
    "ast_get_source_lines",
    "cached_ast_iter_child_nodes",
    "ast_iter_non_node_fields",
    "ast_tree_distance",
    "ast_equal",
]


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


def ast_pretty_dump(
    node: ast.AST, annotate_fields: bool = True, include_attributes: bool = False
) -> str:
    """ Use black formatting library to prettify the dumped AST """

    dumped = ast.dump(node, annotate_fields, include_attributes)

    try:
        import black
        return black.format_str(dumped, mode=black.FileMode())
    except ImportError:
        raise RuntimeError(
            "Black is required to use ast_pretty_dump(). "
            "Try `python pip install -U black` to install."
        )
    except AttributeError:
        # FIXME remove version incompatible check after black publishes the first
        # stable version.
        raise RuntimeError("black version incompatible")


def ast_ordered_walk(node: ast.AST) -> Iterator[ast.AST]:
    """ Depth-First Traversal of the AST """
    children = ast.iter_child_nodes(node)
    for child in children:
        yield child
        yield from ast_ordered_walk(child)


def ast_strip_location_info(node: ast.AST, in_place: bool = True) -> Optional[ast.AST]:
    """ Strip location info from AST nodes, recursively """

    if not in_place:
        new_node = copy.deepcopy(node)
        ast_strip_location_info(new_node, in_place=True)
        return new_node

    nodes = ast_ordered_walk(node)
    location_info_attrs = ("lineno", "col_offset", "end_lineno", "end_col_offset")
    for node in nodes:
        for attr in location_info_attrs:
            if hasattr(node, attr):
                delattr(node, attr)


@profile  # type: ignore
def ast_get_leading_comment_and_decorator_list_source_lines(
    source: str, node: ast.AST
) -> List[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    above_lines = cached_splitlines(source)[: node.lineno - 1]

    decorator_list_linenos: Set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    boundary_lineno = 0  # 0 is a virtual line
    for lineno, line in ireverse(zip(range(1, node.lineno), above_lines)):
        if not (
            len(line.strip()) == 0
            or beginswith(line.lstrip(), "#")
            or lineno in decorator_list_linenos
        ):
            boundary_lineno = lineno
            break

    leading_source_lines = above_lines[boundary_lineno : node.lineno - 1]

    return leading_source_lines


@profile  # type: ignore
def ast_get_leading_comment_source_lines(source: str, node: ast.AST) -> List[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    above_lines = cached_splitlines(source)[: node.lineno - 1]

    decorator_list_linenos: Set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    leading_comment_lines: Deque[str] = deque()
    for lineno, line in ireverse(zip(range(1, node.lineno), above_lines)):
        if lineno in decorator_list_linenos:
            continue
        elif len(line.strip()) == 0 or beginswith(line.lstrip(), "#"):
            leading_comment_lines.appendleft(line)
        else:
            break

    return list(leading_comment_lines)


@profile  # type: ignore
def ast_get_decorator_list_source_lines(source: str, node: ast.AST) -> List[str]:
    """
    Return source lines of the decorator list that decorate a function/class as given
    by the node argument.
    """

    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    source_lines = cached_splitlines(source)

    decorator_list_lines = []
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_lines.extend(source_lines[lineno - 1 : end_lineno])

    return decorator_list_lines


@profile  # type: ignore
def ast_get_source_lines(source: str, node: ast.AST) -> List[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    whole_source_lines = cached_splitlines(source)

    lineno, end_lineno = node.lineno, node.end_lineno
    source_lines = whole_source_lines[lineno - 1 : end_lineno]

    return source_lines


@lfu_cache_with_key(key=id, maxsize=None)
def cached_ast_iter_child_nodes(node: ast.AST) -> List[ast.AST]:
    """ A cached version of the `ast.iter_child_nodes` method """
    return list(ast.iter_child_nodes(node))


def ast_iter_non_node_fields(node: ast.AST) -> Iterator:
    """ Complement of the ast.iter_child_nodes function """

    for _, field in ast.iter_fields(node):
        if isinstance(field, ast.AST):
            continue
        elif isinstance(field, list):
            if all(map(lambda elm: isinstance(elm, ast.AST), field)):
                continue
            elif all(map(lambda elm: not isinstance(elm, ast.AST), field)):
                yield field
            else:
                raise RuntimeError("Unreachable")
        else:
            yield field


def ast_tree_distance(
    node1: ast.AST,
    node2: ast.AST,
    insert_cost: Callable[[ast.AST], float] = None,
    delete_cost: Callable[[ast.AST], float] = None,
    rename_cost: Callable[[ast.AST, ast.AST], float] = None,
) -> float:
    """
    Implementation is Zhang-Shasha's tree edit distance algorithm.

    Reference: https://epubs.siam.org/doi/abs/10.1137/0218082

    Note that the rename_cost function **should** return 0 for identical nodes.
    """

    # Note: one important thing to note here is that, ast.AST() != ast.AST().

    if rename_cost is None:

        # hopefully a sane default
        def default_rename_cost(node1: ast.AST, node2: ast.AST) -> float:
            if type(node1) != type(node2):
                return 1
            else:
                values1 = list(ast_iter_non_node_fields(node1))
                values2 = list(ast_iter_non_node_fields(node2))

                assert len(values1) == len(values2)
                field_length = len(values1)
                if not field_length:
                    return 0

                return hamming_distance(values1, values2) / len(values1)

        rename_cost = default_rename_cost

    return tree_distance(
        node1,
        node2,
        children=compose(list, ast.iter_child_nodes),
        insert_cost=insert_cost,
        delete_cost=delete_cost,
        rename_cost=rename_cost,
    )


def ast_equal(node1: ast.AST, node2: ast.AST) -> bool:
    """ Return if two ast nodes are semantically equal """

    if type(node1) != type(node2):
        return False

    if list(ast_iter_non_node_fields(node1)) != list(ast_iter_non_node_fields(node2)):
        return False

    return all(map(ast_equal, ast.iter_child_nodes(node1), ast.iter_child_nodes(node2)))
