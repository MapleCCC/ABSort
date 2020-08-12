#!/usr/bin/env python3

import ast
import io
from typing import List, Set, Union

import astor
import click

from .ast_utils import ast_ordered_walk, ast_pretty_dump, ast_remove_location_info
from .visitors import GetUndefinedVariableVisitor


DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def get_dependency_of_decl(decl: TYPE_DECL_STMT) -> Set[str]:
    visitor = GetUndefinedVariableVisitor()
    temp_module = ast.Module(body=[decl])
    visitor.visit(temp_module)
    return visitor.undefined_variables


def absort_decls(decls: List[TYPE_DECL_STMT]) -> List[TYPE_DECL_STMT]:
    infos = {}
    for decl in decls:
        infos[decl] = get_dependency_of_decl(decl)
    return []


def transform(top_level_stmts: List[ast.stmt]) -> List[ast.stmt]:
    new_stmts: List[ast.stmt] = []
    buffer: List[TYPE_DECL_STMT] = []
    for stmt in top_level_stmts:
        if isinstance(stmt, DECL_STMT_CLASSES):
            buffer.append(stmt)
        else:
            if buffer:
                new_stmts.extend(absort_decls(buffer))
                buffer.clear()
            new_stmts.append(stmt)
    new_stmts.extend(absort_decls(buffer))
    return new_stmts


def preliminary_sanity_check(top_level_stmts: List[ast.stmt]) -> None:
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

    top_level_stmts = module_tree.body

    preliminary_sanity_check(top_level_stmts)

    new_stmts = transform(top_level_stmts)

    new_module_tree = ast.Module(body=new_stmts)

    ast_remove_location_info(new_module_tree)
    ast.fix_missing_locations(new_module_tree)
    print(astor.to_source(new_module_tree))


if __name__ == "__main__":
    main()
