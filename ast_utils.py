import ast
from typing import Any, Iterator

import black

__all__ = ["ast_pretty_dump", "ast_ordered_walk", "ast_remove_location_info"]


def ast_pretty_dump(node: ast.AST, *args: Any, **kwargs: Any) -> str:
    dumped = ast.dump(node, *args, **kwargs)
    try:
        prettied = black.format_str(dumped, mode=black.FileMode())
    except AttributeError:
        raise RuntimeError("black version incompatible")
    return prettied


def ast_ordered_walk(node: ast.AST) -> Iterator[ast.AST]:
    """ Depth-First Traversal of the AST """
    children = ast.iter_child_nodes(node)
    for child in children:
        yield child
        yield from ast_ordered_walk(child)


def ast_remove_location_info(node: ast.AST) -> None:
    """ in-place """
    nodes = ast_ordered_walk(node)
    location_info_attrs = ("lineno", "col_offset", "end_lineno", "end_col_offset")
    for node in nodes:
        for attr in location_info_attrs:
            if hasattr(node, attr):
                delattr(node, attr)
