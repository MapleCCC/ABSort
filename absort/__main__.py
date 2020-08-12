#!/usr/bin/env python3

import ast
from pathlib import Path
from typing import Iterator, List, Set, Tuple, Union

import astor
import click

from .ast_utils import ast_remove_location_info
from .graph import Graph
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
        # More advanced option is to utilize power of machine learning to put two
        # visually similar function/class definition near each other.
        return sorted(names)

    graph = Graph()
    for decl in decls:
        deps = get_dependency_of_decl(decl)
        for dep in deps:
            graph.add_edge(decl.name, dep)
    sorted_names = graph.topological_sort(same_rank_sorter=same_rank_sorter)
    for name in sorted_names:
        yield from filter(lambda decl: decl.name == name, decls)


def transform(module_tree: ast.Module) -> ast.Module:
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

    new_module_tree = ast.Module(body=new_stmts)

    ast_remove_location_info(new_module_tree)
    ast.fix_missing_locations(new_module_tree)

    return new_module_tree


def preliminary_sanity_check(module_tree: ast.Module) -> None:
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
# TODO in-place
# TODO multi thread
# TODO fix main to bottom
def main(filenames: Tuple[str]) -> None:

    for filename in filenames:
        module_tree = ast.parse(Path(filename).read_text(encoding="utf-8"))

        preliminary_sanity_check(module_tree)

        new_module_tree = transform(module_tree)

        # TODO add more styled output (e.g. colorized)
        print("---------------------------------------")
        print(filename)
        print("***************************************")
        print(astor.to_source(new_module_tree))
        print("***************************************")
        print()


if __name__ == "__main__":
    main()
