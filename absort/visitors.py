import ast
from typing import List, Set, Union

__all__ = ["GetUndefinedVariableVisitor"]


def get_funcdef_arg_names(
    funcdef: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda]
) -> Set[str]:
    arguments = funcdef.args
    args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    if arguments.vararg:
        args.append(arguments.vararg)
    if arguments.kwarg:
        args.append(arguments.kwarg)
    arg_names = {arg.arg for arg in args}
    return arg_names


def get_descendant_names(node: ast.AST) -> Set[str]:
    descendants = ast.walk(node)
    names = [node for node in descendants if isinstance(node, ast.Name)]
    identifiers = {name.id for name in names}
    return identifiers


# TODO order by their appearance in https://docs.python.org/3/library/ast.html#abstract-grammar
# TODO add runtime type checking
# TODO fill in docstring to elaborate on details.
class GetUndefinedVariableVisitor(ast.NodeVisitor):
    """

    """

    def __init__(self) -> None:
        super().__init__()
        self._undefined_vars: Set[str] = set()
        self._symbol_table_stack: List[Set[str]] = []

    __slots__ = ("_undefined_vars", "_symbol_table_stack")

    def visit(self, node: ast.AST) -> Set[str]:
        super().visit(node)
        return self._undefined_vars

    # FIXME no need to traverse in reverse order
    def _symbol_table_lookup(self, name: str) -> bool:
        for symbol_table in self._symbol_table_stack[::-1]:
            if name in symbol_table:
                return True
        return False

    ########################################################################
    # Handle language constructs that introduce new scopes (and possibly new names)
    ########################################################################

    def visit_Module(self, node: ast.Module) -> None:
        self._symbol_table_stack.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    # TODO what is the node.returns attribute?
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        self._symbol_table_stack.append(set())

        arg_names = get_funcdef_arg_names(node)
        self._symbol_table_stack[-1].update(arg_names)

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

        self._symbol_table_stack[-1].add(node.name)

    # TODO what is the node.returns attribute?
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        self._symbol_table_stack.append(set())

        arg_names = get_funcdef_arg_names(node)
        self._symbol_table_stack[-1].update(arg_names)

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

        self._symbol_table_stack[-1].add(node.name)

    # TODO what is the node.keywords attribute?
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        for base in node.bases:
            self.visit(base)

        self._symbol_table_stack.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

        self._symbol_table_stack[-1].add(node.name)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)

        self._symbol_table_stack.append(set())

        # FIXME I am not sure this is correct
        target_names = get_descendant_names(node.target)
        self._symbol_table_stack[-1].update(target_names)

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.iter)

        self._symbol_table_stack.append(set())

        # FIXME I am not sure this is correct
        target_names = get_descendant_names(node.target)
        self._symbol_table_stack[-1].update(target_names)

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)

        self._symbol_table_stack.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)

        self._symbol_table_stack.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack[-1].clear()

        for stmt in node.orelse:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_With(self, node: ast.With) -> None:
        introduced_names: Set[str] = set()

        for withitem in node.items:
            self.visit(withitem.context_expr)

            if optional_vars := withitem.optional_vars:
                # FIXME I am not sure this is correct
                optional_var_names = get_descendant_names(optional_vars)
                introduced_names.update(optional_var_names)

        self._symbol_table_stack.append(set())

        self._symbol_table_stack[-1].update(introduced_names)

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        introduced_names: Set[str] = set()

        for withitem in node.items:
            self.visit(withitem.context_expr)

            if optional_vars := withitem.optional_vars:
                # FIXME I am not sure this is correct
                optional_var_names = get_descendant_names(optional_vars)
                introduced_names.update(optional_var_names)

        self._symbol_table_stack.append(set())

        self._symbol_table_stack[-1].update(introduced_names)

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_Try(self, node: ast.Try) -> None:
        self._symbol_table_stack.append(set())

        for stmt in node.body:
            self.visit(stmt)

        self._symbol_table_stack.pop()

        for handler in node.handlers:
            if handler.type:
                self.visit(handler.type)

            self._symbol_table_stack.append(set())

            if handler.name:
                self._symbol_table_stack[-1].add(handler.name)

            for stmt in handler.body:
                self.visit(stmt)

            self._symbol_table_stack.pop()

        self._symbol_table_stack.append(set())

        for stmt in node.orelse:
            self.visit(stmt)

        self._symbol_table_stack[-1].clear()

        for stmt in node.finalbody:
            self.visit(stmt)

        self._symbol_table_stack.pop()

    def visit_ListComp(self, node: ast.ListComp) -> None:
        nested_level = 0

        for generator in node.generators:
            self.visit(generator.iter)

            self._symbol_table_stack.append(set())

            # FIXME I am not sure this is correct
            target_names = get_descendant_names(generator.target)
            self._symbol_table_stack[-1].update(target_names)

            # No need to actually create scope for every if_test
            for if_test in generator.ifs:
                self.visit(if_test)

            nested_level += 1

        self.visit(node.elt)

        for _ in range(nested_level):
            self._symbol_table_stack.pop()

    def visit_SetComp(self, node: ast.SetComp) -> None:
        nested_level = 0

        for generator in node.generators:
            self.visit(generator.iter)

            self._symbol_table_stack.append(set())

            # FIXME I am not sure this is correct
            target_names = get_descendant_names(generator.target)
            self._symbol_table_stack[-1].update(target_names)

            # No need to actually create scope for every if_test
            for if_test in generator.ifs:
                self.visit(if_test)

            nested_level += 1

        self.visit(node.elt)

        for _ in range(nested_level):
            self._symbol_table_stack.pop()

    def visit_DictComp(self, node: ast.DictComp) -> None:
        nested_level = 0

        for generator in node.generators:
            self.visit(generator.iter)

            self._symbol_table_stack.append(set())

            # FIXME I am not sure this is correct
            target_names = get_descendant_names(generator.target)
            self._symbol_table_stack[-1].update(target_names)

            # No need to actually create scope for every if_test
            for if_test in generator.ifs:
                self.visit(if_test)

            nested_level += 1

        self.visit(node.key)
        self.visit(node.value)

        for _ in range(nested_level):
            self._symbol_table_stack.pop()

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        nested_level = 0

        for generator in node.generators:
            self.visit(generator.iter)

            self._symbol_table_stack.append(set())

            # FIXME I am not sure this is correct
            target_names = get_descendant_names(generator.target)
            self._symbol_table_stack[-1].update(target_names)

            for if_test in generator.ifs:
                self.visit(if_test)

            nested_level += 1

        self.visit(node.elt)

        for _ in range(nested_level):
            self._symbol_table_stack.pop()

    ########################################################################
    # Handle stmts that introduce new symbols, or delete existing symbols
    ########################################################################

    def visit_Delete(self, node: ast.Delete) -> None:
        # FIXME I am not sure this is correct
        # WARNING: this is not correct. This code currently can't handle the case of
        # deleting attribute references, subscriptions, slicing, etc.
        # e.g. `del a.b, a[1], a[1:2]`
        to_delete_names = get_descendant_names(node)
        for name in to_delete_names:
            # FIXME we need to change the lookup scope to the scopes that are
            # allowed by the `del` keyword, as per the Python language grammar.
            if name in self._symbol_table_stack[-1]:
                self._symbol_table_stack[-1].remove(name)
            else:
                # there is no corresponding name in local scope
                self._undefined_vars.add(name)

    def visit_Import(self, node: ast.Import) -> None:
        aliases = node.names
        for alias in aliases:
            if alias.asname:
                self._symbol_table_stack[-1].add(alias.asname)
            else:
                self._symbol_table_stack[-1].add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        aliases = node.names
        for alias in aliases:
            if alias.asname:
                self._symbol_table_stack[-1].add(alias.asname)
            else:
                self._symbol_table_stack[-1].add(alias.name)

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            # FIXME we need to narrow down the lookup scope to global scope, the scope
            # that are allowed by the `global` keyword, as per the Python language
            # grammar.
            if self._symbol_table_lookup(name):
                self._symbol_table_stack[-1].add(name)
            else:
                # there is no corresponding name in outter scopes
                self._undefined_vars.add(name)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            # FIXME we need to narrow down the lookup scope to the scopes that are
            # allowed by the `nonlocal` keyword, as per the Python language grammar.
            if self._symbol_table_lookup(name):
                self._symbol_table_stack[-1].add(name)
            else:
                # there is no corresponding name in outter scopes
                self._undefined_vars.add(name)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            if self._symbol_table_lookup(node.id):
                pass
            else:
                self._symbol_table_stack[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            if self._symbol_table_lookup(node.id):
                pass
            else:
                self._undefined_vars.add(node.id)
        else:
            # TODO fill in cases for contexts Del, AugLoad, AugStore, Param
            raise NotImplementedError

    # TODO fill and complete
