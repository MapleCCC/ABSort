import ast
from collections import deque
from typing import Any, Deque, Iterator, List, Set

from .utils import beginswith, cached_splitlines, ireverse, lfu_cache_with_key

__all__ = [
    "ast_pretty_dump",
    "ast_ordered_walk",
    "ast_remove_location_info",
    "ast_get_leading_comment_and_decorator_list_source_lines",
    "ast_get_leading_comment_source_lines",
    "ast_get_decorator_list_source_lines",
    "ast_get_source_lines",
    "cached_ast_iter_child_nodes",
]


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


def ast_pretty_dump(node: ast.AST, *args: Any, **kwargs: Any) -> str:
    """ Use black formatting library to prettify the dumped AST """

    dumped = ast.dump(node, *args, **kwargs)
    try:
        # fmt: off
        import black
        prettied = black.format_str(dumped, mode=black.FileMode())
        # fmt: on
    except ImportError:
        raise RuntimeError(
            "Black is required to use ast_pretty_dump(). "
            "Try `python pip install -U black` to install."
        )
    except AttributeError:
        # FIXME remove version incompatible check after black publishes the first
        # stable version.
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
    return list(ast.iter_child_nodes(node))
