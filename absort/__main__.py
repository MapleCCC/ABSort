#!/usr/bin/env python3

import ast
import io
from typing import Iterator, List, Set, Union

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
    graph = Graph()
    for decl in decls:
        deps = get_dependency_of_decl(decl)
        for dep in deps:
            graph.add_edge(decl.name, dep)
    sorted_names = graph.topological_sort()
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
@click.argument("file", type=click.File("r", encoding="utf-8"))
# TODO in-place
# TODO multi thread
# TODO fix main to bottom
def main(file: io.TextIOWrapper) -> None:
    module_tree = ast.parse(file.read())

    preliminary_sanity_check(module_tree)

    new_module_tree = transform(module_tree)

    print(astor.to_source(new_module_tree))


if __name__ == "__main__":
    main()
