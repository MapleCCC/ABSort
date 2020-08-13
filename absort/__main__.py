#!/usr/bin/env python3

import ast
from itertools import takewhile
from pathlib import Path
from typing import Iterator, List, Set, Tuple, Union

import click

from .iblack8 import format_code
from .graph import Graph
from .utils import reverse, beginswith, colored_unified_diff
from .visitors import GetUndefinedVariableVisitor


DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def get_dependency_of_decl(decl: TYPE_DECL_STMT) -> Set[str]:
    temp_module = ast.Module(body=[decl])
    visitor = GetUndefinedVariableVisitor()
    return visitor.visit(temp_module)


def absort_decls(decls: List[TYPE_DECL_STMT]) -> Iterator[TYPE_DECL_STMT]:
    def same_rank_sorter(names: List[str]) -> List[str]:
        # Currently sort by lexigraphical order.
        # Alternatives: sort by body size, sort by name length, etc.
        # TODO More advanced option is to utilize power of machine learning to put two
        # visually/semantically similar function/class definitions near each other.
        return sorted(names)

    graph = Graph()
    for decl in decls:
        deps = get_dependency_of_decl(decl)
        for dep in deps:
            graph.add_edge(decl.name, dep)
    sorted_names = list(graph.topological_sort(same_rank_sorter=same_rank_sorter))

    cli_params = click.get_current_context().params
    if not cli_params["no_fix_main_to_bottom"] and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    for name in sorted_names:
        yield from filter(lambda decl: decl.name == name, decls)


def transform(old_source: str) -> str:
    module_tree = ast.parse(old_source)

    top_level_stmts = module_tree.body

    new_stmts: List[ast.stmt] = []
    buffer: List[TYPE_DECL_STMT] = []
    for stmt in top_level_stmts:
        if isinstance(stmt, DECL_STMT_CLASSES):
            buffer.append(stmt)
        else:
            new_stmts.extend(absort_decls(buffer))
            buffer.clear()
            new_stmts.append(stmt)
    new_stmts.extend(absort_decls(buffer))

    new_source = ""
    for stmt in new_stmts:
        leading_lines = old_source.splitlines()[: stmt.lineno - 1]
        white_criteria = lambda line: len(line.strip()) == 0 or beginswith(line, "#")
        white_section = reverse(takewhile(white_criteria, leading_lines[::-1]))
        new_source += "\n".join(white_section) + "\n"

        segment = ast.get_source_segment(old_source, stmt, padded=True)
        new_source += segment + "\n"

    return new_source


def preliminary_sanity_check(source_code: str) -> None:
    # TODO add more sanity checks

    module_tree = ast.parse(source_code)
    top_level_stmts = module_tree.body
    decls = [stmt for stmt in top_level_stmts if isinstance(stmt, DECL_STMT_CLASSES)]
    decl_ids = [decl.name for decl in decls]

    if len(decl_ids) != len(set(decl_ids)):
        raise ValueError("Name redefinition exists. Not supported yet.")


@click.command()
@click.argument(
    "filenames",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, readable=True, allow_dash=True),
)
@click.option("-d", "--diff", "display_diff", is_flag=True)
@click.option("--no-fix-main-to-bottom", is_flag=True)
# TODO in-place
# TODO multi thread
# TODO reserve comments
# TODO reserve blank lines and other whitespaces
def main(
    filenames: Tuple[str], display_diff: bool, no_fix_main_to_bottom: bool
) -> None:

    for filename in filenames:
        old_source = Path(filename).read_text(encoding="utf-8")

        preliminary_sanity_check(old_source)

        new_source = transform(old_source)

        new_source = format_code(new_source)

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
        else:
            print("---------------------------------------")
            print(filename)
            print("***************************************")
            print(new_source)
            print("***************************************")
            print("\n", end="")


if __name__ == "__main__":
    main()
