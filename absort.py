#!/usr/bin/env python3

import ast
import io
from typing import List, Set, Union

import astor
import click

from ast_utils import ast_ordered_walk, ast_pretty_dump, ast_remove_location_info

DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def get_funcdef_arg_ids(
    funcdef: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda]
) -> List[str]:
    arguments = funcdef.args
    args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    if arguments.vararg:
        args.append(arguments.vararg)
    if arguments.kwarg:
        args.append(arguments.kwarg)
    arg_ids = [arg.arg for arg in args]
    return arg_ids


# TODO rename to less obscure function name
def get_descendant_name_ids(node: ast.AST) -> Set[str]:
    descendants = ast.walk(node)
    names = [node for node in descendants if isinstance(node, ast.Name)]
    ids = {name.id for name in names}
    return ids


# TODO rename dependency to undefined-variable/name/symbol
# TODO order by their appearance in https://docs.python.org/3/library/ast.html#abstract-grammar
# TODO add runtime type checking
class GetDependencyVisitor(ast.NodeVisitor):
    """

    """

    def __init__(self) -> None:
        super().__init__()
        self._deps: Set[str] = set()
        self._env_list: List[Set[str]] = []

    __slots__ = ("_deps", "_env_list")

    # FIXME Should not use verb as name for a @property function
    @property
    def get_dependency(self) -> Set[str]:
        return self._deps

    # FIXME no need to traverse in reverse order
    def _env_lookup(self, id: str) -> bool:
        for env in self._env_list[::-1]:
            if id in env:
                return True
        return False

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            if self._env_lookup(node.id):
                pass
            else:
                self._env_list[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            if self._env_lookup(node.id):
                pass
            else:
                self._deps.add(node.id)
        else:
            # TODO
            raise NotImplementedError

    ########################################################################
    # Handle language constructs that introduce new scopes (and possibly new names)
    ########################################################################

    def visit_Module(self, node: ast.Module) -> None:
        self._env_list = []
        for stmt in node.body:
            self.visit(stmt)

    # TODO what is the node.returns attribute?
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        self._env_list.append(set())

        arg_ids = get_funcdef_arg_ids(node)
        self._env_list[-1].update(arg_ids)

        for stmt in node.body:
            self.visit(stmt)

        self._env_list.pop()

        self._env_list[-1].add(node.name)

    # TODO what is the node.returns attribute?
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        self._env_list.append(set())

        arg_ids = get_funcdef_arg_ids(node)
        self._env_list[-1].update(arg_ids)

        for stmt in node.body:
            self.visit(stmt)

        self._env_list.pop()

        self._env_list[-1].add(node.name)

    # TODO what is the node.keywords attribute?
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        for base in node.bases:
            self.visit(base)

        self._env_list.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._env_list.pop()

        self._env_list[-1].add(node.name)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)

        self._env_list.append(set())

        # FIXME I am not sure this is correct
        target_name_ids = get_descendant_name_ids(node.target)
        self._env_list[-1].update(target_name_ids)

        for stmt in node.body:
            self.visit(stmt)

        self._env_list[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._env_list.pop()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.iter)

        self._env_list.append(set())

        # FIXME I am not sure this is correct
        target_name_ids = get_descendant_name_ids(node.target)
        self._env_list[-1].update(target_name_ids)

        for stmt in node.body:
            self.visit(stmt)

        self._env_list[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._env_list.pop()

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)

        self._env_list.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._env_list[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._env_list.pop()

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)

        self._env_list.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._env_list[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._env_list.pop()

    def visit_With(self, node: ast.With) -> None:
        introduced_names: Set[str] = set()

        for withitem in node.items:
            self.visit(withitem.context_expr)

            optional_vars = withitem.optional_vars
            if optional_vars:
                # FIXME I am not sure this is correct
                optional_var_name_ids = get_descendant_name_ids(optional_vars)
                # self._env_list[-1].update(optional_var_name_ids)
                introduced_names.update(optional_var_name_ids)

        self._env_list.append(set())

        self._env_list[-1].update(introduced_names)

        for stmt in node.body:
            self.visit(stmt)

        self._env_list.pop()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        introduced_names: Set[str] = set()

        for withitem in node.items:
            self.visit(withitem.context_expr)

            optional_vars = withitem.optional_vars
            if optional_vars:
                # FIXME I am not sure this is correct
                optional_var_name_ids = get_descendant_name_ids(optional_vars)
                # self._env_list[-1].update(optional_var_name_ids)
                introduced_names.update(optional_var_name_ids)

        self._env_list.append(set())

        self._env_list[-1].update(introduced_names)

        for stmt in node.body:
            self.visit(stmt)

        self._env_list.pop()

    def visit_Try(self, node: ast.Try) -> None:
        self._env_list.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._env_list.pop()

        handlers = node.handlers

        for handler in handlers:
            if handler.type:
                self.visit(handler.type)
            self._env_list.append(set())
            if handler.name:
                self._env_list[-1].add(handler.name)
            for stmt in handler.body:
                self.visit(stmt)
            self._env_list.pop()

        self._env_list.append(set())

        for stmt in node.orelse:
            self.visit(stmt)

        self._env_list[-1].clear()

        for stmt in node.finalbody:
            self.visit(stmt)

        self._env_list.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._env_list.append(set())

        arg_ids = get_funcdef_arg_ids(node)
        self._env_list[-1].update(arg_ids)

        self.visit(node.body)

        self._env_list.pop()

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._env_list.append(set())

        self.visit(node.body)

        self._env_list[-1].clear()

        self.visit(node.orelse)

        self._env_list.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._env_list.append(set())
        for generator in node.generators:
            pass
        self._env_list[-1]

    ########################################################################
    # Handle stmts that introduce new symbols, or delete existing symbols
    ########################################################################

    def visit_Delete(self, node: ast.Delete) -> None:
        # FIXME I am not sure this is correct
        name_ids = get_descendant_name_ids(node)
        for id in name_ids:
            # FIXME Should we use set.remove (raise KeyError if not contained) or
            # set.discard (remove if present)?
            self._env_list[-1].remove(id)

    def visit_Import(self, node: ast.Import) -> None:
        aliases = node.names
        for alias in aliases:
            if alias.asname:
                self._env_list[-1].add(alias.asname)
            else:
                self._env_list[-1].add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        aliases = node.names
        for alias in aliases:
            if alias.asname:
                self._env_list[-1].add(alias.asname)
            else:
                self._env_list[-1].add(alias.name)

    # FIXME what if there is no corresponding name in outter scopes?
    def visit_Global(self, node: ast.Global) -> None:
        self._env_list[-1].update(node.names)

    # FIXME what if there is no corresponding name in outter scopes?
    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._env_list[-1].update(node.names)

    # TODO fill and complete


def get_dependency_of_decl(decl: TYPE_DECL_STMT) -> Set[str]:
    visitor = GetDependencyVisitor()
    temp_module = ast.Module(body=[decl])
    visitor.visit(temp_module)
    return visitor.get_dependency


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
