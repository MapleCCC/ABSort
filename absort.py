#!/usr/bin/env python3

import ast
import io
from pprint import PrettyPrinter
from typing import Iterator, List, Set, Union

import astor
import click

pprint = PrettyPrinter().pprint


DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def ast_ordered_walk(node: ast.AST) -> Iterator[ast.AST]:
    """ Depth-First Traversal of the AST """
    children = ast.iter_child_nodes(node)
    for child in children:
        yield child
        yield from ast_ordered_walk(child)


def get_funcdef_arg_ids(
    funcdef: Union[ast.FunctionDef, ast.AsyncFunctionDef]
) -> List[str]:
    arguments = funcdef.args
    args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    if arguments.vararg:
        args.append(arguments.vararg)
    if arguments.kwarg:
        args.append(arguments.kwarg)
    arg_ids = [arg.arg for arg in args]
    return arg_ids


def get_dependency_of_decl(decl: TYPE_DECL_STMT) -> Set[str]:
    descendants = ast_ordered_walk(decl)

    # TODO rename to bound_ids
    store_cxt_name_ids = []
    if isinstance(decl, (ast.FunctionDef, ast.AsyncFunctionDef)):
        arg_ids = get_funcdef_arg_ids(decl)
        store_cxt_name_ids.extend(arg_ids)

    names = [node for node in descendants if isinstance(node, ast.Name)]

    deps = set()

    for name in names:
        if isinstance(name.ctx, ast.Store):
            store_cxt_name_ids.append(name.id)
        elif isinstance(name.ctx, ast.Load):
            if name.id in store_cxt_name_ids:
                # FIXME IT'S NOT THAT SIMPLE!!!
                pass
            else:
                deps.add(name.id)
        else:
            raise NotImplementedError

    return deps


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


def ast_remove_location_info(node: ast.AST) -> None:
    """ in-place """
    nodes = ast_ordered_walk(node)
    for node in nodes:
        delattr(node, "lineno")
        delattr(node, "col_offset")
        delattr(node, "end_lineno")
        delattr(node, "end_col_offset")


def preliminary_sanity_check(top_level_stmts: List[ast.stmt]) -> None:
    decls = [stmt for stmt in top_level_stmts if isinstance(stmt, DECL_STMT_CLASSES)]
    decl_ids = [decl.name for decl in decls]
    if len(decl_ids) != len(set(decl_ids)):
        raise ValueError("Name redefinition exists. Not supported yet.")


@click.command()
@click.argument("file", type=click.File("r", encoding="utf-8"))
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
