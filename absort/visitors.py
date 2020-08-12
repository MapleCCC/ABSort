import ast
from enum import Enum, auto
from typing import Iterable, List, Set, Union

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


class ScopeContext(Enum):
    Module = auto()
    Function = auto()
    Class = auto()
    For = auto()
    ForElse = auto()
    While = auto()
    WhileElse = auto()
    If = auto()
    IfElse = auto()
    With = auto()
    Try = auto()
    ExceptHandler = auto()
    TryElse = auto()
    TryFinal = auto()


# TODO order by their appearance in https://docs.python.org/3/library/ast.html#abstract-grammar
# TODO add runtime type checking. @runtime_type_check
# TODO fill in docstring to elaborate on details.
# TODO @assert_symtab_stack_depth
class GetUndefinedVariableVisitor(ast.NodeVisitor):
    """

    """

    def __init__(self) -> None:
        super().__init__()
        self._undefined_vars: Set[str] = set()
        self._scope_context_stack: List[ScopeContext] = []
        self._symbol_table_stack: List[Set[str]] = []
        self._declaration_name_table_stack: List[Set[str]] = []

    __slots__ = (
        "_undefined_vars",
        "_scope_stack",
        "_symbol_table_stack",
        "_declaration_name_table_stack",
    )

    def visit(self, node: ast.AST) -> Set[str]:
        super().visit(node)
        return self._undefined_vars

    def _symbol_lookup(self, name: str) -> bool:
        # FIXME no need to traverse in reverse order
        def symbol_table_lookup(name: str) -> bool:
            for symbol_table in self._symbol_table_stack[::-1]:
                if name in symbol_table:
                    return True
            return False

        # FIXME no need to traverse in reverse order
        def declaration_name_table_lookup(name: str) -> bool:
            for declaration_symbol_table in self._declaration_name_table_stack[::-1]:
                if name in declaration_symbol_table:
                    return True
            return False

        in_decl_context = False
        for scope_ctx in self._scope_context_stack:
            if scope_ctx in (ScopeContext.Function, ScopeContext.Class):
                in_decl_context = True

        if in_decl_context:
            return symbol_table_lookup(name) or declaration_name_table_lookup(name)
        else:
            return symbol_table_lookup(name)

    def _visit_new_scope(
        self,
        nodes: List[ast.AST],
        scope_ctx: ScopeContext,
        inject_names: Set[str] = None,
    ) -> None:
        self._scope_context_stack.append(scope_ctx)

        self._symbol_table_stack.append(set())
        if inject_names:
            self._symbol_table_stack[-1].update(inject_names)

        def collect_visible_declarations(nodes: Iterable[ast.AST]) -> Set[str]:
            visible_decls = set()
            for node in nodes:
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    visible_decls.add(node.name)
                else:
                    visible_decls.update(
                        collect_visible_declarations(ast.iter_child_nodes(node))
                    )
            return visible_decls

        visible_decls = collect_visible_declarations(nodes)
        self._declaration_name_table_stack.append(visible_decls)

        for node in nodes:
            self.visit(node)

        self._declaration_name_table_stack.pop()
        self._symbol_table_stack.pop()
        self._scope_context_stack.pop()

    ########################################################################
    # Handle language constructs that introduce new scopes (and possibly new names)
    ########################################################################

    def visit_Module(self, node: ast.Module) -> None:
        self._visit_new_scope(node.body, ScopeContext.Module)

    # TODO what is the node.returns attribute?
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        inject_names = set()

        # Allow recursion
        inject_names.add(node.name)

        arg_names = get_funcdef_arg_names(node)
        inject_names.update(arg_names)

        self._visit_new_scope(node.body, ScopeContext.Function, inject_names)

        func_name_visible_scope_index = len(self._scope_context_stack) - 1
        for index, scope_ctx in enumerate(self._scope_context_stack[::-1]):
            if scope_ctx in (
                ScopeContext.Module,
                ScopeContext.Function,
                ScopeContext.Class,
            ):
                func_name_visible_scope_index = (
                    len(self._scope_context_stack) - 1 - index
                )
        self._symbol_table_stack[func_name_visible_scope_index].add(node.name)

    # TODO what is the node.returns attribute?
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        inject_names = set()

        # Allow recursion
        inject_names.add(node.name)

        arg_names = get_funcdef_arg_names(node)
        inject_names.update(arg_names)

        self._visit_new_scope(node.body, ScopeContext.Function, inject_names)

        func_name_visible_scope_index = len(self._scope_context_stack) - 1
        for index, scope_ctx in enumerate(self._scope_context_stack[::-1]):
            if scope_ctx in (
                ScopeContext.Module,
                ScopeContext.Function,
                ScopeContext.Class,
            ):
                func_name_visible_scope_index = (
                    len(self._scope_context_stack) - 1 - index
                )
        self._symbol_table_stack[func_name_visible_scope_index].add(node.name)

    # TODO what is the node.keywords attribute?
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)

        for base in node.bases:
            self.visit(base)

        self._visit_new_scope(node.body, ScopeContext.Class, inject_names={node.name})

        class_name_visible_scope_index = len(self._scope_context_stack) - 1
        for index, scope_ctx in enumerate(self._scope_context_stack[::-1]):
            if scope_ctx in (
                ScopeContext.Module,
                ScopeContext.Function,
                ScopeContext.Class,
            ):
                class_name_visible_scope_index = (
                    len(self._scope_context_stack) - 1 - index
                )
        self._symbol_table_stack[class_name_visible_scope_index].add(node.name)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)

        # FIXME I am not sure this is correct
        target_names = get_descendant_names(node.target)

        self._visit_new_scope(node.body, ScopeContext.For, inject_names=target_names)

        self._visit_new_scope(node.orelse, ScopeContext.ForElse)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.iter)

        # FIXME I am not sure this is correct
        target_names = get_descendant_names(node.target)

        self._visit_new_scope(node.body, ScopeContext.For, inject_names=target_names)

        self._visit_new_scope(node.orelse, ScopeContext.ForElse)

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)

        self._visit_new_scope(node.body, ScopeContext.While)

        self._visit_new_scope(node.orelse, ScopeContext.WhileElse)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)

        self._visit_new_scope(node.body, ScopeContext.If)

        self._visit_new_scope(node.orelse, ScopeContext.IfElse)

    def visit_With(self, node: ast.With) -> None:
        introduced_names: Set[str] = set()

        for withitem in node.items:
            self.visit(withitem.context_expr)

            if optional_vars := withitem.optional_vars:
                # FIXME I am not sure this is correct
                optional_var_names = get_descendant_names(optional_vars)
                introduced_names.update(optional_var_names)

        self._visit_new_scope(
            node.body, ScopeContext.With, inject_names=introduced_names
        )

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        introduced_names: Set[str] = set()

        for withitem in node.items:
            self.visit(withitem.context_expr)

            if optional_vars := withitem.optional_vars:
                # FIXME I am not sure this is correct
                optional_var_names = get_descendant_names(optional_vars)
                introduced_names.update(optional_var_names)

        self._visit_new_scope(
            node.body, ScopeContext.With, inject_names=introduced_names
        )

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_new_scope(node.body, ScopeContext.Try)

        for handler in node.handlers:
            if handler.type:
                self.visit(handler.type)

            inject_names = set()
            if handler.name:
                inject_names.add(handler.name)

            self._visit_new_scope(
                handler.body, ScopeContext.ExceptHandler, inject_names=inject_names
            )

        self._visit_new_scope(node.orelse, ScopeContext.TryElse)

        self._visit_new_scope(node.finalbody, ScopeContext.TryFinal)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        # Bottom-up building new node
        new_tree: ast.stmt = ast.Expr(value=node.elt)
        for generator in node.generators:
            for if_test in generator.ifs:
                new_tree = ast.If(test=if_test, body=[new_tree])
            new_tree = ast.For(
                target=generator.target, iter=generator.iter, body=[new_tree]
            )

        self.visit(new_tree)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        # Bottom-up building new node
        new_tree: ast.stmt = ast.Expr(value=node.elt)
        for generator in node.generators:
            for if_test in generator.ifs:
                new_tree = ast.If(test=if_test, body=[new_tree])
            new_tree = ast.For(
                target=generator.target, iter=generator.iter, body=[new_tree]
            )

        self.visit(new_tree)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        # Bottom-up building new node
        new_tree: ast.stmt = ast.Expr(
            value=ast.Tuple(elts=[node.key, node.value], ctx=ast.Load())
        )
        for generator in node.generators:
            for if_test in generator.ifs:
                new_tree = ast.If(test=if_test, body=[new_tree])
            new_tree = ast.For(
                target=generator.target, iter=generator.iter, body=[new_tree]
            )

        self.visit(new_tree)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        # Bottom-up building new node
        new_tree: ast.stmt = ast.Expr(value=node.elt)
        for generator in node.generators:
            for if_test in generator.ifs:
                new_tree = ast.If(test=if_test, body=[new_tree])
            new_tree = ast.For(
                target=generator.target, iter=generator.iter, body=[new_tree]
            )

        self.visit(new_tree)

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
            if self._symbol_lookup(name):
                self._symbol_table_stack[-1].add(name)
            else:
                # there is no corresponding name in outter scopes
                self._undefined_vars.add(name)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            # FIXME we need to narrow down the lookup scope to the scopes that are
            # allowed by the `nonlocal` keyword, as per the Python language grammar.
            if self._symbol_lookup(name):
                self._symbol_table_stack[-1].add(name)
            else:
                # there is no corresponding name in outter scopes
                self._undefined_vars.add(name)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            if self._symbol_lookup(node.id):
                pass
            else:
                self._symbol_table_stack[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            if self._symbol_lookup(node.id):
                pass
            else:
                self._undefined_vars.add(node.id)
        else:
            # TODO fill in cases for contexts Del, AugLoad, AugStore, Param
            raise NotImplementedError

    # TODO fill and complete
