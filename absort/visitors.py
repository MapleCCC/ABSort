import ast
from collections.abc import Sequence as Seq

from recipes.exceptions import Unreachable
from typing_extensions import assert_never

from .typing_extra import PyVersion


__all__ = ["GetUndefinedVariableVisitor"]


# TODO the abstract grammar is changed started from CPython 3.9, update accordingly.
# E.g., starargs and kwargs of ClassDef from https://docs.python.org/3/library/ast.html#ast.ClassDef,
# though they don't show up in the abstract grammar from https://docs.python.org/3/library/ast.html#abstract-grammar.
# Why the inconsistency? Try to parse a source to figure out.

# TODO Read through the new Python 3.9 ast doc, to see if any thing has updated and need
# to be changed in this module.

# TODO read the doc of libCST, and see if there are inconsistencies between libCST and
# ast. Whether libCST can be used as a drop-in replacement of the builtin ast module or
# not?


def retrieve_names_from_args(args: ast.arguments) -> set[str]:
    names: set[str] = set()
    names.update(arg.arg for arg in args.posonlyargs)
    names.update(arg.arg for arg in args.args)
    names.update(arg.arg for arg in args.kwonlyargs)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


class BogusNode(ast.AST):
    pass


# TODO fill in docstring to elaborate on details
# Class methods are ordered by their appearance order in https://docs.python.org/3/library/ast.html#abstract-grammar
class GetUndefinedVariableVisitor(ast.NodeVisitor):
    """
    An ast node visitor that implements the logic to retrieve undefined variables.

    Usage:
    ```
    undefined_vars = GetUndefinedVariableVisitor().visit(some_ast_node)
    ```
    """

    def __init__(self, py_version: PyVersion) -> None:
        super().__init__()

        self._undefined_vars: set[str] = set()
        self._namespaces: list[dict[str, ast.AST]] = []
        self._py_version: PyVersion = py_version

    __slots__ = ("_undefined_vars", "_namespaces", "_py_version")

    def _symbol_lookup(self, name: str) -> ast.AST | None:
        for namespace in reversed(self._namespaces):
            if name in namespace:
                return namespace[name]
        return None

    def visit(self, node: ast.AST) -> set[str]:
        super().visit(node)
        return self._undefined_vars

    def _visit(self, obj: ast.AST | Seq[ast.AST] | None) -> None:
        """
        A handy helper method that can accept either an ast node, or None, or a list of ast nodes.
        This method is aimed to simplify programming, relieving wordy code.
        """

        if obj is None:
            return
        elif isinstance(obj, ast.AST):
            self.visit(obj)
        elif isinstance(obj, Seq):
            for node in obj:
                self.visit(node)
        else:
            assert_never(obj)

    def visit_Module(self, node: ast.Module) -> None:
        self._namespaces.append({})
        self._visit(node.body)
        self._namespaces.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit(node.decorator_list)
        self._visit(node.returns)

        # WARNING: inject function name before proceeding to visit function body,
        # because it's possible the function name is accessed inside the function body.
        self._namespaces[-1][node.name] = node

        self._namespaces.append({})

        for name in retrieve_names_from_args(node.args):
            self._namespaces[-1][name] = BogusNode()

        self._visit(node.body)

        self._namespaces.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit(node.decorator_list)
        self._visit(node.returns)

        # WARNING: inject function name before proceeding to visit function body,
        # because it's possible the function name is accessed inside the function body.
        self._namespaces[-1][node.name] = node

        self._namespaces.append({})

        for name in retrieve_names_from_args(node.args):
            self._namespaces[-1][name] = BogusNode()

        self._visit(node.body)

        self._namespaces.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit(node.bases)
        self._visit(node.keywords)
        self._visit(node.decorator_list)
        # WARNING: inject class name before proceeding to visit class body, because it's
        # possible the class name is accessed inside the class body.
        self._namespaces[-1][node.name] = node
        self._namespaces.append({})
        self._visit(node.body)
        self._namespaces.pop()

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            self._namespaces[-1][name.asname or name.name] = BogusNode()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for name in node.names:
            self._namespaces[-1][name.asname or name.name] = BogusNode()

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self._namespaces[-1][name] = BogusNode()

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            self._namespaces[-1][name] = BogusNode()

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
        elt: ast.expr,
    ) -> None:
        """
        A helper method to implement shared logic among visit_ListComp, visit_SetComp,
        visit_DictComp, and visit_GeneratorExp.
        """

        # Bottom-up building new tree
        new_tree: ast.stmt = ast.Expr(value=elt)
        for generator in reversed(node.generators):
            for if_test in reversed(generator.ifs):
                new_tree = ast.If(test=if_test, body=[new_tree], orelse=[])
            new_tree = ast.For(
                target=generator.target,
                iter=generator.iter,
                body=[new_tree],
                orelse=[],
                type_comment=None,
            )

        self._visit(new_tree)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node, node.elt)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node, node.elt)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        elt = ast.Tuple(elts=[node.key, node.value], ctx=ast.Load())
        self._visit_comprehension(node, elt)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node, node.elt)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if not self._symbol_lookup(node.id):
                self._undefined_vars.add(node.id)

        elif isinstance(node.ctx, ast.Store):
            # TODO if we found the symbol, should we update it in the namespace?
            if not self._symbol_lookup(node.id):
                self._namespaces[-1][node.id] = node

        elif isinstance(node.ctx, ast.Del):
            for namespace in reversed(self._namespaces):
                if node.id in namespace:
                    del namespace[node.id]
                    break

        else:
            raise Unreachable
