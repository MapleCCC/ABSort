import ast
from itertools import takewhile
from typing import Any, Iterator, Optional

import black

from .extra_typing import Decoratable
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


# FIXME can't handle multi-line decorator expression
def ast_get_leading_comment_source_segment(
    source: str, node: ast.AST, padded: bool = False
) -> str:
    whitespace_filter = lambda line: len(line.strip()) == 0
    comment_filter = lambda line: beginswith(line.lstrip(), "#")
    decorator_filter = lambda line: beginswith(line.lstrip(), "@")

    # WARNING: ast.AST.lineno is 1-indexed
    leading_lines = source.splitlines()[: node.lineno - 1]

    white_criteria = (
        lambda line: whitespace_filter(line)
        or comment_filter(line)
        # It's possible to have comments between decorator_list and function/class definition
        or decorator_filter(line)
    )
    white_section = reverse(takewhile(white_criteria, leading_lines[::-1]))

    comments = list(filter(comment_filter, white_section))

    if not padded:
        comments = list(map(str.lstrip, comments))

    if comments:
        return "\n".join(comments) + "\n"
    else:
        return ""


def ast_get_decorator_list_source_segment(
    source: str, node: ast.AST, padded: bool = False
) -> Optional[str]:
    """
    Return source segment of the decorator list that decorate a function/class as given
    by the node argument.

    If some location information is missing, return None.
    """

    if not isinstance(node, Decoratable):
        return ""

    # We need to check existence of the attribute decorator_list, because some
    # ast.FunctionDef node doesn't have decorator_list attribute. This could happen if
    # the node is initialized manually instead of initialized from parsing code.
    if not hasattr(node, "decorator_list"):
        return ""

    decorator_list_source_segment = ""
    for decorator in node.decorator_list:
        decorator_source_segment = ast.get_source_segment(
            source, decorator, padded=padded
        )
        if decorator_source_segment is None:
            raise ValueError(
                "Location info is missing. "
                "Get source segment of decorator_list failed."
            )
        pad_length = len(decorator_source_segment) - len(
            decorator_source_segment.lstrip()
        )
        decorator_source_segment = (
            decorator_source_segment[:pad_length]
            + "@"
            + decorator_source_segment[pad_length:]
        )
        decorator_list_source_segment += decorator_source_segment + "\n"
    return decorator_list_source_segment
