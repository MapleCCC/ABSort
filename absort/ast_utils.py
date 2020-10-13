import ast
import copy
import re
from collections import deque
from collections.abc import Iterator
from numbers import Number
from typing import Optional, Union

from .treedist import pqgram, zhangshasha
from .utils import (
    beginswith,
    cached_splitlines,
    constantfunc,
    hamming_distance,
    identityfunc,
    iequal,
    ireverse,
    memoization,
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
    "ast_tree_edit_distance",
    "ast_shallow_equal",
    "ast_deep_equal",
    "ast_tree_size",
]


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = identityfunc


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


def ast_get_leading_comment_and_decorator_list_source_lines(
    source: str, node: ast.AST
) -> list[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    above_lines = cached_splitlines(source)[: node.lineno - 1]

    decorator_list_linenos: set[int] = set()
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


def ast_get_leading_comment_source_lines(source: str, node: ast.AST) -> list[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    above_lines = cached_splitlines(source)[: node.lineno - 1]

    decorator_list_linenos: set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    leading_comment_lines: deque[str] = deque()
    for lineno, line in ireverse(zip(range(1, node.lineno), above_lines)):
        if lineno in decorator_list_linenos:
            continue
        elif len(line.strip()) == 0 or beginswith(line.lstrip(), "#"):
            leading_comment_lines.appendleft(line)
        else:
            break

    return list(leading_comment_lines)


def ast_get_decorator_list_source_lines(source: str, node: ast.AST) -> list[str]:
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


def ast_get_source_lines(source: str, node: ast.AST) -> list[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    whole_source_lines = cached_splitlines(source)

    lineno, end_lineno = node.lineno, node.end_lineno
    source_lines = whole_source_lines[lineno - 1 : end_lineno]

    return source_lines


@memoization(key=id)
def cached_ast_iter_child_nodes(node: ast.AST) -> list[ast.AST]:
    """ A cached version of the `ast.iter_child_nodes` method """
    return list(ast.iter_child_nodes(node))


@memoization(key=id)
def ast_node_class_fields(ast_node_class: type[ast.AST]) -> list[tuple[str, str]]:
    assert hasattr(ast_node_class, "__doc__")
    schema = ast_node_class.__doc__
    assert schema
    m = re.fullmatch(r"\w+(?:\((?P<attributes>.*)\))?", schema)
    if m is None:
        raise ValueError
    attributes = m.group("attributes")
    if attributes is None:
        return []
    return [tuple(attribute.split()) for attribute in attributes.split(",")]  # type: ignore


# Reference: https://docs.python.org/3/library/ast.html#abstract-grammar
Terminals = ("identifier", "int", "string", "constant")
# Reference: https://docs.python.org/3/library/ast.html#ast.Constant
TerminalType = Union[str, Number, None, tuple, frozenset]


def ast_iter_non_node_fields(
    node: ast.AST,
) -> Iterator[Union[TerminalType, list[TerminalType], None]]:
    """ Complement of the ast.iter_child_nodes function """

    for type, name in ast_node_class_fields(node.__class__):
        if type.rstrip("?*") in Terminals:
            yield getattr(node, name)


def ast_tree_edit_distance(
    node1: ast.AST, node2: ast.AST, algorithm: str = "ZhangShasha"
) -> float:
    """
    Implementation is Zhang-Shasha's tree edit distance algorithm.

    Reference: https://epubs.siam.org/doi/abs/10.1137/0218082

    Note that the rename_cost function **should** return 0 for identical nodes.
    """

    # Note: one important thing to note here is that, ast.AST() != ast.AST().

    if algorithm == "ZhangShasha":
        # hopefully a sane default
        def rename_cost(node1: ast.AST, node2: ast.AST) -> float:
            return 1 - ast_shallow_equal(node1, node2)

        return zhangshasha(
            node1,
            node2,
            children=ast.iter_child_nodes,
            insert_cost=constantfunc(1),
            delete_cost=constantfunc(1),
            rename_cost=rename_cost,
        )

    elif algorithm == "PQGram":
        return pqgram(node1, node2, children=ast.iter_child_nodes, label=type)

    else:
        raise ValueError("Invalid value for the algorithm argument")


def ast_shallow_equal(node1: ast.AST, node2: ast.AST) -> float:
    """
    Return if two ast nodes are equal, by comparing shallow level data
    Return zero if non-equal, and positive numbers if partially equal or completely equal

    For advanced usage, the returned positive number is a fraction between 0 and 1,
    denoting how equal the two nodes are. The closer to 1 the more equal, and vice versa.
    """

    if type(node1) != type(node2):
        return 0

    fields1 = list(ast_iter_non_node_fields(node1))
    fields2 = list(ast_iter_non_node_fields(node2))
    assert len(fields1) == len(fields2)
    field_length = len(fields1)
    if not field_length:
        return 1
    return 1 - (hamming_distance(fields1, fields2) / len(fields1))


def ast_deep_equal(node1: ast.AST, node2: ast.AST) -> bool:
    """ Return if two ast nodes are semantically equal """

    if type(node1) != type(node2):
        return False

    if list(ast_iter_non_node_fields(node1)) != list(ast_iter_non_node_fields(node2)):
        return False

    return iequal(
        ast.iter_child_nodes(node1),
        ast.iter_child_nodes(node2),
        equal=ast_deep_equal,
        strict=True,
    )


def ast_tree_size(node: ast.AST) -> int:
    return 1 + sum(map(ast_tree_size, ast.iter_child_nodes(node)))
