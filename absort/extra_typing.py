import ast
from typing import Union

__all__ = ["Declaration", "Declarationtype", "Decoratable", "DecoratableType"]

Declaration = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
DeclarationType = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]

Decoratable = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
DecoratableType = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]
