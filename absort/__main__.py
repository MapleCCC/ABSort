#!/usr/bin/env python3

import ast
from pathlib import Path
from typing import Iterator, List, Set, Tuple

import click
import colorama
from more_itertools import first_true

from .ast_utils import (
    ast_get_leading_comment_source_segment,
    ast_get_decorator_list_source_segment,
)
from .extra_typing import DeclarationType, Declaration
from .graph import Graph
from .utils import colored_unified_diff
from .visitors import GetUndefinedVariableVisitor


def get_dependency_of_decl(decl: DeclarationType) -> Set[str]:
    temp_module = ast.Module(body=[decl])
    visitor = GetUndefinedVariableVisitor()
    return visitor.visit(temp_module)


def absort_decls(decls: List[DeclarationType]) -> Iterator[DeclarationType]:
    def same_rank_sorter(names: List[str]) -> List[str]:
        # Currently sort by lexigraphical order.
        # Possible alternatives: sort by body size, sort by name length, etc.
        # TODO More advanced option is to utilize power of machine learning to put two
        # visually/semantically similar function/class definitions near each other.
        return sorted(names)

    decl_names = [decl.name for decl in decls]
    if len(set(decl_names)) < len(decl_names):
        raise ValueError("Name redefinition exists. Not supported yet.")

    graph = Graph()
    for decl in decls:
        deps = get_dependency_of_decl(decl)
        for dep in deps:
            if dep in decl_names:
                graph.add_edge(decl.name, dep)
    sorted_names = list(graph.topological_sort(same_rank_sorter=same_rank_sorter))

    cli_params = click.get_current_context().params

    if cli_params["reverse"]:
        sorted_names.reverse()

    if not cli_params["no_fix_main_to_bottom"] and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    # Only one decl matches the name, we use short-circuit to optimize.
    for name in sorted_names:
        name_matcher = lambda decl: decl.name == name
        yield first_true(decls, pred=name_matcher)  # type: ignore


def transform(old_source: str) -> str:
    module_tree = ast.parse(old_source)

    top_level_stmts = module_tree.body

    new_stmts: List[ast.stmt] = []
    buffer: List[DeclarationType] = []
    for stmt in top_level_stmts:
        if isinstance(stmt, Declaration):
            buffer.append(stmt)
        else:
            new_stmts.extend(absort_decls(buffer))
            buffer.clear()
            new_stmts.append(stmt)
    new_stmts.extend(absort_decls(buffer))

    # FIXME no need to specify `padded=True`, because they are all top-level statements.

    new_source = ""
    for stmt in new_stmts:
        new_source += ast_get_leading_comment_source_segment(
            old_source, stmt, padded=True
        )

        # WARNING: it's surprising that ast.get_source_segment doesn't include source
        # segment of decorator_list.
        new_source += ast_get_decorator_list_source_segment(
            old_source, stmt, padded=True
        )

        new_source += ast.get_source_segment(old_source, stmt, padded=True)

        new_source += "\n\n"

    # Only reserve one trailing newline
    if new_source.endswith("\n\n"):
        new_source = new_source[:-1]

    return new_source


def preliminary_sanity_check(source_code: str) -> None:
    # TODO add more sanity checks

    module_tree = ast.parse(source_code)
    top_level_stmts = module_tree.body
    decls = [stmt for stmt in top_level_stmts if isinstance(stmt, Declaration)]
    decl_names = [decl.name for decl in decls]

    if len(set(decl_names)) < len(decl_names):
        raise ValueError("Name redefinition exists. Not supported yet.")


@click.command()
@click.argument(
    "filenames",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, readable=True, allow_dash=True),
)
@click.option("-d", "--diff", "display_diff", is_flag=True)
@click.option("-i", "--in-place", is_flag=True)
@click.option("--no-fix-main-to-bottom", is_flag=True)
@click.option("-r", "--reverse", is_flag=True)
@click.option("-e", "--encoding", default="utf-8")
# TODO add multi thread support, to accelerate
# TODO add option "--comment-is-attribute-of-following-declaration"
def main(
    filenames: Tuple[str],
    display_diff: bool,
    in_place: bool,
    no_fix_main_to_bottom: bool,
    reverse: bool,
    encoding: str,
) -> None:

    if display_diff and in_place:
        raise RuntimeError("Can't specify both `--diff` and `--in-place` options")

    colorama.init()

    for filename in filenames:
        old_source = Path(filename).read_text(encoding)

        preliminary_sanity_check(old_source)

        new_source = transform(old_source)

        # TODO add more styled output (e.g. colorized)

        if display_diff:
            old_src_lines = old_source.splitlines(keepends=True)
            new_src_lines = new_source.splitlines(keepends=True)
            fromfile = "old/" + filename
            tofile = "new/" + filename
            diff_view_lines = colored_unified_diff(
                old_src_lines, new_src_lines, fromfile, tofile
            )
            print("".join(diff_view_lines), end="")
            print("\n", end="")
        elif in_place:
            Path(filename).write_text(new_source, encoding)
        else:
            print("---------------------------------------")
            print(filename)
            print("***************************************")
            print(new_source)
            print("***************************************")
            print("\n", end="")


if __name__ == "__main__":
    main()
