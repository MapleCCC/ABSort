import ast
from typing import Union

__all__ = ["DECL_STMT_CLASSES", "TYPE_DECL_STMT", "Decoratable"]

DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]

Decoratable = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]
