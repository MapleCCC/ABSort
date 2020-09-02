import ast
from typing import Dict, List, Optional, Set, Sequence, Union


__all__ = ["GetUndefinedVariableVisitor"]


def retrieve_names_from_args(args: ast.arguments) -> Set[str]:
    names = set()
    names.update(arg.arg for arg in args.posonlyargs)
    names.update(arg.arg for arg in args.args)
    names.update(arg.arg for arg in args.kwonlyargs)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


class DummyNode(ast.AST):
    pass


class GetUndefinedVariableVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self._undefined_vars: Set[str] = set()
        self._namespaces: List[Dict[str, ast.AST]] = []

    __slots__ = ("_undefined_vars", "_namespaces")

    def _symbol_lookup(self, name: str) -> Optional[ast.AST]:
        for namespace in reversed(self._namespaces):
            if name in namespace:
                return namespace[name]
        return None

    def visit(self, node: ast.AST) -> Set[str]:
        super().visit(node)
        return self._undefined_vars

    def _visit(self, obj: Union[Sequence[ast.AST], Optional[ast.AST]]) -> None:
        if isinstance(obj, list):
            for node in obj:
                self.visit(node)
        elif isinstance(obj, ast.AST):
            self.visit(obj)
        elif obj is None:
            return
        else:
            raise ValueError

    def visit_Module(self, node: ast.Module) -> None:
        self._namespaces.append({})
        self._visit(node.body)
        self._namespaces.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit(node.decorator_list)
        self._visit(node.returns)
        self._namespaces[-1][node.name] = node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit(node.decorator_list)
        self._visit(node.returns)
        self._namespaces[-1][node.name] = node

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit(node.bases)
        self._visit(node.keywords)
        self._visit(node.decorator_list)
        self._namespaces[-1][node.name] = node

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            if name.asname:
                self._namespaces[-1][name.asname] = DummyNode()
            else:
                self._namespaces[-1][name.name] = DummyNode()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for name in node.names:
            if name.asname:
                self._namespaces[-1][name.asname] = DummyNode()
            else:
                self._namespaces[-1][name.name] = DummyNode()

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self._namespaces[-1][name] = DummyNode()

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            self._namespaces[-1][name] = DummyNode()

    def _visit_comprehension(
        self,
        node: Union[ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp],
        elt: ast.expr,
    ) -> None:
        # Bottom-up building new tree
        new_tree: ast.stmt = ast.Expr(value=elt)
        for generator in reversed(node.generators):
            for if_test in generator.ifs:
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

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            self.generic_visit(node)
            return

        self._visit(node.args)
        self._visit(node.keywords)

        _node = self._symbol_lookup(node.func.id)
        if _node is None:
            self._undefined_vars.add(node.func.id)
            return

        if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._namespaces.append({})
            for name in retrieve_names_from_args(_node.args):
                self._namespaces[-1][name] = DummyNode()
            self._visit(_node.body)
            self._namespaces.pop()
        elif isinstance(_node, ast.ClassDef):
            self._namespaces.append({})
            self._visit(_node.body)
            self._namespaces.pop()
        else:
            # Encounter a supposedly runtime error, we as a static tool,
            # should not alert about it.
            return

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if not self._symbol_lookup(node.id):
                self._undefined_vars.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            if not self._symbol_lookup(node.id):
                self._namespaces[-1][node.id] = node
        elif isinstance(node.ctx, ast.Del):
            for namespace in reversed(self._namespaces):
                if node.id in namespace:
                    del namespace[node.id]
                    break
        else:
            # Read Green Tree Snakes docs.
            # AugLoad, AugStore, Param
            raise NotImplementedError
