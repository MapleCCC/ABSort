import ast
from collections import deque
from typing import Dict, List, Optional, Set, Sequence, Tuple, Union

from .extra_exceptions import NameRedefinition
from .profile_tools import add_profile_decorator_to_class_methods


__all__ = ["GetUndefinedVariableVisitor"]


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


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


# FIXME Can class __init__ method be async function?
def retrieve_init_method(cls: ast.ClassDef) -> Optional[ast.FunctionDef]:
    candidates = [
        stmt
        for stmt in cls.body
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__"
    ]
    if not candidates:
        return None
    if len(candidates) > 1:
        raise SyntaxError("Class definition contains duplicate __init__ methods")
    init_method = candidates[0]
    return init_method


class _DummyNode(ast.AST):
    pass


# TODO fill in docstring to elaborate on details
# Class methods are ordered by their appearance order in https://docs.python.org/3/library/ast.html#abstract-grammar
@add_profile_decorator_to_class_methods
class GetUndefinedVariableVisitor(ast.NodeVisitor):
    """
    An ast node visitor that implements the logic to retrieve undefined variables.

    Usage:
    ```
    undefined_vars = GetUndefinedVariableVisitor().visit(some_ast_node)
    ```
    """

    def __init__(self, py_version: Tuple[int, int]) -> None:
        self._undefined_vars: Set[str] = set()
        self._namespaces: List[Dict[str, ast.AST]] = []
        self._call_stack: List[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = []
        self._py_version: Tuple[int, int] = py_version

    __slots__ = ("_undefined_vars", "_namespaces", "_call_stack", "_py_version")

    def _symbol_lookup(self, name: str) -> Optional[ast.AST]:
        for namespace in reversed(self._namespaces):
            if name in namespace:
                return namespace[name]
        return None

    def visit(self, node: ast.AST) -> Set[str]:
        super().visit(node)
        return self._undefined_vars

    def _visit(self, obj: Union[Sequence[ast.AST], Optional[ast.AST]]) -> None:
        """
        A handy helper method that can accept either an ast node, or None, or a list of ast nodes.
        This method is aimed to simplify programming, relieving wordy code.
        """

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
        # WARNING: inject class name before proceeding to visit class body, because it's
        # possible the class name is accessed inside the class body.
        self._namespaces[-1][node.name] = node
        self._namespaces.append({})
        self._visit(node.body)
        self._namespaces.pop()

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            if name.asname:
                self._namespaces[-1][name.asname] = _DummyNode()
            else:
                self._namespaces[-1][name.name] = _DummyNode()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for name in node.names:
            if name.asname:
                self._namespaces[-1][name.asname] = _DummyNode()
            else:
                self._namespaces[-1][name.name] = _DummyNode()

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self._namespaces[-1][name] = _DummyNode()

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            self._namespaces[-1][name] = _DummyNode()

    def _visit_comprehension(
        self,
        node: Union[ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp],
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

    def visit_Call(self, node: ast.Call) -> None:
        def visit_name_call(node: ast.Call) -> None:
            assert isinstance(node.func, ast.Name)

            self._visit(node.args)
            self._visit(node.keywords)

            _node = self._symbol_lookup(node.func.id)
            if _node is None:
                self._undefined_vars.add(node.func.id)
                return

            if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function = _node
            elif isinstance(_node, ast.ClassDef):
                function = retrieve_init_method(_node)
                if function is None:
                    # As a static analysis tool, we can't handle heavily dynamic behavior.
                    # So just skipping here should be a good decision.
                    return
            else:
                # As a static analysis tool, we can't handle heavily dynamic behavior.
                # So just skipping here should be a good decision.
                return

            if function in self._call_stack:
                # Break out from recursion
                return

            self._call_stack.append(function)
            self._namespaces.append({})

            if self._py_version >= (3, 9):
                self._visit(function.args)
            else:
                for name in retrieve_names_from_args(function.args):
                    self._namespaces[-1][name] = _DummyNode()

            self._visit(function.body)

            self._namespaces.pop()
            self._call_stack.pop()

        def visit_attr_call(node: ast.Call) -> None:
            def ast_get_attr_node(node: ast.AST, target_attr: str)->ast.AST:
                if not isinstance(node, ast.ClassDef):
                    raise NotImplementedError

                attrs = {}
                for stmt in node.body:
                    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if stmt.name in attrs:
                            raise NameRedefinition
                        attrs[stmt.name] = stmt
                    elif isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                if target.id in attrs:
                                    raise NameRedefinition
                                attrs[target.id] = target
                            else:
                                raise NotImplementedError
                    else:
                        raise NotImplementedError

                return attrs[target_attr]

            assert isinstance(node.func, ast.Attribute)

            self._visit(node.args)
            self._visit(node.keywords)

            top_level = node.func.value
            attrs = deque()

            while isinstance(top_level, ast.Attribute):
                attrs.appendleft(top_level.attr)
                top_level = top_level.value

            if isinstance(top_level, ast.Name):
                _node = self._symbol_lookup(top_level.id)
                if _node is None:
                    self._undefined_vars.add(top_level.id)

                if isinstance(_node, ast.ClassDef):
                    attribute = _node
                    for attr in attrs:
                        if not isinstance(attribute, ast.ClassDef):
                            # As a static analysis tool, we can't handle heavily dynamic behavior.
                            # So just skipping here should be a good decision.
                            return
                        attribute = ast_get_attr_node(attribute, attr)

                    if not isinstance(attribute, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # As a static analysis tool, we can't handle heavily dynamic behavior.
                        # So just skipping here should be a good decision.
                        return

                    if attribute in self._call_stack:
                        # Break out from recursion
                        return

                    self._call_stack.append(attribute)
                    self._namespaces.append({})

                    if self._py_version >= (3, 9):
                        self._visit(attribute.args)
                    else:
                        for name in retrieve_names_from_args(attribute.args):
                            self._namespaces[-1][name] = _DummyNode()

                    self._visit(attribute.body)

                    self._namespaces.pop()
                    self._call_stack.pop()

                else:
                    # As a static analysis tool, we can't handle heavily dynamic behavior.
                    # So just skipping here should be a good decision.
                    return
            else:
                self._visit(node.func.value)

        if isinstance(node.func, ast.Name):
            visit_name_call(node)
        elif isinstance(node.func, ast.Attribute):
            visit_attr_call(node)
        else:
            self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        # Expression context AugLoad and AugStore are never exposed. (https://bugs.python.org/issue39988)
        # We only need to deal with Load, Store, Del, and Param.

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
        elif isinstance(node.ctx, ast.Param):
            self._namespaces[-1][node.id] = node
