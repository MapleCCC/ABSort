import ast
from itertools import takewhile
from typing import Any, Iterator

import black

from .utils import reverse, beginswith


__all__ = [
    "ast_pretty_dump",
    "ast_ordered_walk",
    "ast_remove_location_info",
    "ast_get_leading_comment_source_segment",
    "ast_get_decorator_list_source_segment",
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


def ast_get_leading_comment_source_segment(
    source: str, node: ast.AST, padded: bool = False
) -> str:
    # WARNING: ast.AST.lineno is 1-indexed
    leading_lines = source.splitlines()[: node.lineno - 1]
    white_criteria = (
        lambda line: len(line.strip()) == 0
        or beginswith(line.lstrip(), "#")
        or beginswith(line.lstrip(), "@")
    )
    white_section = reverse(takewhile(white_criteria, leading_lines[::-1]))

    comments = filter(lambda line: beginswith(line.lstrip(), "#"), white_section)

    if not padded:
        comments = map(str.lstrip, comments)

    return "\n".join(comments) + "\n"


def ast_get_decorator_list_source_segment(
    source: str, node: ast.AST, padded: bool = False
) -> str:
    if not hasattr(node, "decorator_list"):
        return ""

    decorator_list_source_segment = ""
    for decorator in node.decorator_list:  # type: ignore
        decorator_source_segment = "@" + ast.get_source_segment(
            source, decorator, padded=padded
        )
        decorator_list_source_segment += decorator_source_segment + "\n"
    return decorator_list_source_segment
