import ast
from collections import deque
from typing import Any, Deque, Iterator, Set

import black

from .utils import beginswith, reverse

__all__ = [
    "ast_pretty_dump",
    "ast_ordered_walk",
    "ast_remove_location_info",
    "ast_get_leading_comment_and_decorator_list_source_segment",
    "ast_get_leading_comment_source_segment",
    "ast_get_decorator_list_source_segment",
    "ast_get_source_segment",
]


def ast_pretty_dump(node: ast.AST, *args: Any, **kwargs: Any) -> str:
    """ Use black formatting library to prettify the dumped AST """

    dumped = ast.dump(node, *args, **kwargs)
    try:
        prettied = black.format_str(dumped, mode=black.FileMode())
    except AttributeError:
        raise RuntimeError("black version incompatible")
    return prettied


# FIXME are you sure that ast.iter_child_nodes() returned result is ordered?
def ast_ordered_walk(node: ast.AST) -> Iterator[ast.AST]:
    """ Depth-First Traversal of the AST """
    children = ast.iter_child_nodes(node)
    for child in children:
        yield child
        yield from ast_ordered_walk(child)


# TODO Alternatively, we can have a non-in-place version. Try to compare the benefits.
def ast_remove_location_info(node: ast.AST) -> None:
    """ in-place """
    nodes = ast_ordered_walk(node)
    location_info_attrs = ("lineno", "col_offset", "end_lineno", "end_col_offset")
    for node in nodes:
        for attr in location_info_attrs:
            if hasattr(node, attr):
                delattr(node, attr)


# TODO use memoization technique to optimzie performance.
def ast_get_leading_comment_and_decorator_list_source_segment(
    source: str, node: ast.AST
) -> str:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    above_lines = source.splitlines()[: node.lineno - 1]

    decorator_list_linenos: Set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    boundary_lineno = 0  # 0 is a virtual line
    for lineno, line in reverse(zip(range(1, node.lineno - 1), above_lines)):
        if not (
            len(line.strip()) == 0
            or beginswith(line.lstrip(), "#")
            or lineno in decorator_list_linenos
        ):
            boundary_lineno = lineno
            break

    leading_source_lines = above_lines[boundary_lineno : node.lineno - 1]

    return "\n".join(leading_source_lines)


def ast_get_leading_comment_source_segment(source: str, node: ast.AST) -> str:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    above_lines = source.splitlines()[: node.lineno - 1]

    decorator_list_linenos: Set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    leading_comment_lines: Deque[str] = deque()
    for lineno, line in reverse(zip(range(1, node.lineno - 1), above_lines)):
        if len(line.strip()) == 0 or beginswith(line.lstrip(), "#"):
            leading_comment_lines.appendleft(line)
        elif lineno in decorator_list_linenos:
            continue
        else:
            break

    return "\n".join(leading_comment_lines)


def ast_get_decorator_list_source_segment(source: str, node: ast.AST) -> str:
    """
    Return source segment of the decorator list that decorate a function/class as given
    by the node argument.
    """

    source_lines = source.splitlines()

    decorator_list_lines = []
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_lines.extend(source_lines[lineno - 1 : end_lineno])

    return "\n".join(decorator_list_lines)


def ast_get_source_segment(source: str, node: ast.AST) -> str:
    source_lines = source.splitlines()
    lineno, end_lineno = node.lineno, node.end_lineno
    return "\n".join(source_lines[lineno - 1 : end_lineno])
