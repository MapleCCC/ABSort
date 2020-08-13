#!/usr/bin/env python3

import ast
import difflib
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple, Union

import astor
import click

from .ast_utils import ast_remove_location_info
from .iblack8 import format_code
from .graph import Graph
from .visitors import GetUndefinedVariableVisitor


DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def get_dependency_of_decl(decl: TYPE_DECL_STMT) -> Set[str]:
    temp_module = ast.Module(body=[decl])
    visitor = GetUndefinedVariableVisitor()
    return visitor.visit(temp_module)


def absort_decls(
    decls: List[TYPE_DECL_STMT], options: Dict[str, Any]
) -> Iterator[TYPE_DECL_STMT]:
    def same_rank_sorter(names: List[str]) -> List[str]:
        # Currently sort by lexigraphical order.
        # TODO More advanced option is to utilize power of machine learning to put two
        # visually/semantically similar function/class definitions near each other.
        return sorted(names)

    graph = Graph()
    for decl in decls:
        deps = get_dependency_of_decl(decl)
        for dep in deps:
            graph.add_edge(decl.name, dep)
    sorted_names = list(graph.topological_sort(same_rank_sorter=same_rank_sorter))

    if options["no_fix_main_to_bottom"] and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    for name in sorted_names:
        yield from filter(lambda decl: decl.name == name, decls)


def transform(module_tree: ast.Module, options: Dict[str, Any]) -> ast.Module:
    top_level_stmts = module_tree.body

    new_stmts: List[ast.stmt] = []
    buffer: List[TYPE_DECL_STMT] = []
    for stmt in top_level_stmts:
        if isinstance(stmt, DECL_STMT_CLASSES):
            buffer.append(stmt)
        else:
            new_stmts.extend(absort_decls(buffer, options))
            buffer.clear()
            new_stmts.append(stmt)
    new_stmts.extend(absort_decls(buffer, options))

    new_module_tree = ast.Module(body=new_stmts)

    ast_remove_location_info(new_module_tree)
    ast.fix_missing_locations(new_module_tree)

    return new_module_tree


def preliminary_sanity_check(module_tree: ast.Module) -> None:
    # TODO add more sanity checks

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
# TODO fix main to bottom
# TODO keep comments
def main(filenames: Tuple[str], display_diff: bool, no_fix_main_to_bottom: bool) -> None:

    for filename in filenames:
        old_source = Path(filename).read_text(encoding="utf-8")

        module_tree = ast.parse(old_source)

        preliminary_sanity_check(module_tree)

        options = {"no_fix_main_to_bottom": no_fix_main_to_bottom}
        new_module_tree = transform(module_tree, options)

        new_source = astor.to_source(new_module_tree)

        new_source = format_code(new_source)

        # TODO add more styled output (e.g. colorized)
        print("---------------------------------------")
        print(filename)
        print("***************************************")

        if display_diff:
            old_src_lines = old_source.splitlines()
            new_src_lines = new_source.splitlines()
            print("\n".join(difflib.unified_diff(old_src_lines, new_src_lines)))
        else:
            print(new_source)

        print("***************************************")
        print("\n", end="")


if __name__ == "__main__":
    main()
