from __future__ import annotations

import ast
from collections.abc import Iterator
from functools import cache
from typing import TYPE_CHECKING, Literal, cast

from typing_extensions import Self

from .astutils import (
    TerminalType,
    ast_tree_size,
    ast_tree_edit_distance,
    ast_deep_equal,
    ast_get_source,
    ast_iter_non_node_fields,
    ast_ordered_walk,
    ast_pretty_dump,
)
from .typing_extra import PyVersion
from .visitors import GetUndefinedVariableVisitor


__all__ = ["NeoAST", "parse", "Declaration", "Decoratable"]


# XXX weak ref dict
# @cache
# XXX Shouldn't cache, it's a ephemeral call.
def ast_hash(node: ast.AST) -> int:
    return hash(NeoAST(node))


# XXX enforce truly immutable


class NeoAST(ast.AST):
    """
    Enhanced AST class.

    1. Immutable/frozen/hashable/equalable.
    2. Ordered walking.
    3. Pretty dump.
    4. Extract source.
    5. Edit distance.
    6. Symbol table stats.
    """

    # def __init__(self, *args, **kwargs) -> None:
    #     super().__init__(*args, **kwargs)
    #     self._hash = None

    # __slots__ = "_hash"

    __slots__ = ()

    def size(self) -> int:
        return ast_tree_size(self)

    def attributes(self) -> Iterator[TerminalType | list[TerminalType] | None]:
        return ast_iter_non_node_fields(self)

    def children(self) -> Iterator[Self]:
        for node in ast.iter_child_nodes(self):
            yield self.__class__(node)

    def walk(self) -> Iterator[Self]:
        for node in ast_ordered_walk(self):
            yield self.__class__(node)

    def dump(
        self,
        annotate_fields: bool = True,
        include_attributes: bool = False,
        black_formatted: bool = False,
    ) -> str:
        dump = ast_pretty_dump if black_formatted else ast.dump
        return dump(self, annotate_fields, include_attributes)

    def source(self, source: str) -> str:
        return ast_get_source(source, self)

    def edit_distance(
        self,
        other: ast.AST,
        algorithm: Literal["ZhangShasha", "PQGram"] = "ZhangShasha",
    ) -> float:
        return ast_tree_edit_distance(self, other, algorithm)

    def free_symbols(self, py_version: PyVersion) -> set[str]:
        temp_module = ast.Module(body=[self], type_ignores=[])
        visitor = GetUndefinedVariableVisitor(py_version)
        return visitor.visit(temp_module)

    def __equal__(self, other: Self) -> bool:
        return ast_deep_equal(self, other)

    @property
    @cache
    def hashvalue(self) -> int:
        tup = (self.__class__, tuple(self.attributes()), tuple(self.children()))
        return hash(tup)

    def __hash__(self) -> int:
        return self.hashvalue

    # def __hash__(self) -> int:
    #     if self._hash is None:
    #         tup = (self.__class__, tuple(self.attributes()), tuple(self.children()))
    #         self._hash = hash(tup)
    #     return self._hash

    # TODO properly type annotate the `feature_version` parameter. Why typeshed says
    # feature_version can be int ?

    @classmethod
    def from_source(
        cls, source: str, *, feature_version: PyVersion | None = None
    ) -> Module:
        return cast(Module, cls(ast.parse(source, feature_version=feature_version)))


AST = NeoAST


parse = NeoAST.from_source


# fmt: off
class Add(ast.Add, NeoAST): __slots__ = ()
class And(ast.And, NeoAST): __slots__ = ()
class AnnAssign(ast.AnnAssign, NeoAST): __slots__ = ()
class Assert(ast.Assert, NeoAST): __slots__ = ()
class Assign(ast.Assign, NeoAST): __slots__ = ()
class AsyncFor(ast.AsyncFor, NeoAST): __slots__ = ()
class AsyncFunctionDef(ast.AsyncFunctionDef, NeoAST): __slots__ = ()
class AsyncWith(ast.AsyncWith, NeoAST): __slots__ = ()
class Attribute(ast.Attribute, NeoAST): __slots__ = ()
class AugAssign(ast.AugAssign, NeoAST): __slots__ = ()
class AugLoad(ast.AugLoad, NeoAST): __slots__ = ()
class AugStore(ast.AugStore, NeoAST): __slots__ = ()
class Await(ast.Await, NeoAST): __slots__ = ()
class BinOp(ast.BinOp, NeoAST): __slots__ = ()
class BitAnd(ast.BitAnd, NeoAST): __slots__ = ()
class BitOr(ast.BitOr, NeoAST): __slots__ = ()
class BitXor(ast.BitXor, NeoAST): __slots__ = ()
class BoolOp(ast.BoolOp, NeoAST): __slots__ = ()
class Break(ast.Break, NeoAST): __slots__ = ()
class Bytes(ast.Bytes, NeoAST): __slots__ = ()
class Call(ast.Call, NeoAST): __slots__ = ()
class ClassDef(ast.ClassDef, NeoAST): __slots__ = ()
class Compare(ast.Compare, NeoAST): __slots__ = ()
class Constant(ast.Constant, NeoAST): __slots__ = ()
class Continue(ast.Continue, NeoAST): __slots__ = ()
class Del(ast.Del, NeoAST): __slots__ = ()
class Delete(ast.Delete, NeoAST): __slots__ = ()
class Dict(ast.Dict, NeoAST): __slots__ = ()
class DictComp(ast.DictComp, NeoAST): __slots__ = ()
class Div(ast.Div, NeoAST): __slots__ = ()
class Ellipsis(ast.Ellipsis, NeoAST): __slots__ = ()
class Eq(ast.Eq, NeoAST): __slots__ = ()
class ExceptHandler(ast.ExceptHandler, NeoAST): __slots__ = ()
class Expr(ast.Expr, NeoAST): __slots__ = ()
class Expression(ast.Expression, NeoAST): __slots__ = ()
class ExtSlice(ast.ExtSlice, NeoAST): __slots__ = ()
class FloorDiv(ast.FloorDiv, NeoAST): __slots__ = ()
class For(ast.For, NeoAST): __slots__ = ()
class FormattedValue(ast.FormattedValue, NeoAST): __slots__ = ()
class FunctionDef(ast.FunctionDef, NeoAST): __slots__ = ()
class FunctionType(ast.FunctionType, NeoAST): __slots__ = ()
class GeneratorExp(ast.GeneratorExp, NeoAST): __slots__ = ()
class Global(ast.Global, NeoAST): __slots__ = ()
class Gt(ast.Gt, NeoAST): __slots__ = ()
class GtE(ast.GtE, NeoAST): __slots__ = ()
class If(ast.If, NeoAST): __slots__ = ()
class IfExp(ast.IfExp, NeoAST): __slots__ = ()
class Import(ast.Import, NeoAST): __slots__ = ()
class ImportFrom(ast.ImportFrom, NeoAST): __slots__ = ()
class In(ast.In, NeoAST): __slots__ = ()
class Index(ast.Index, NeoAST): __slots__ = ()
class Interactive(ast.Interactive, NeoAST): __slots__ = ()
class Invert(ast.Invert, NeoAST): __slots__ = ()
class Is(ast.Is, NeoAST): __slots__ = ()
class IsNot(ast.IsNot, NeoAST): __slots__ = ()
class JoinedStr(ast.JoinedStr, NeoAST): __slots__ = ()
class LShift(ast.LShift, NeoAST): __slots__ = ()
class Lambda(ast.Lambda, NeoAST): __slots__ = ()
class List(ast.List, NeoAST): __slots__ = ()
class ListComp(ast.ListComp, NeoAST): __slots__ = ()
class Load(ast.Load, NeoAST): __slots__ = ()
class Lt(ast.Lt, NeoAST): __slots__ = ()
class LtE(ast.LtE, NeoAST): __slots__ = ()
class MatMult(ast.MatMult, NeoAST): __slots__ = ()
class Match(ast.Match, NeoAST): __slots__ = ()
class MatchAs(ast.MatchAs, NeoAST): __slots__ = ()
class MatchClass(ast.MatchClass, NeoAST): __slots__ = ()
class MatchMapping(ast.MatchMapping, NeoAST): __slots__ = ()
class MatchOr(ast.MatchOr, NeoAST): __slots__ = ()
class MatchSequence(ast.MatchSequence, NeoAST): __slots__ = ()
class MatchSingleton(ast.MatchSingleton, NeoAST): __slots__ = ()
class MatchStar(ast.MatchStar, NeoAST): __slots__ = ()
class MatchValue(ast.MatchValue, NeoAST): __slots__ = ()
class Mod(ast.Mod, NeoAST): __slots__ = ()
class Module(ast.Module, NeoAST):
    __slots__ = ()
    def __init__(self) -> None:
        super().__init__()
        self.body: list[stmt] = [stmt(s) for s in super().body]
class Mult(ast.Mult, NeoAST): __slots__ = ()
class Name(ast.Name, NeoAST): __slots__ = ()
class NameConstant(ast.NameConstant, NeoAST): __slots__ = ()
class NamedExpr(ast.NamedExpr, NeoAST): __slots__ = ()
class Nonlocal(ast.Nonlocal, NeoAST): __slots__ = ()
class Not(ast.Not, NeoAST): __slots__ = ()
class NotEq(ast.NotEq, NeoAST): __slots__ = ()
class NotIn(ast.NotIn, NeoAST): __slots__ = ()
class Num(ast.Num, NeoAST): __slots__ = ()
class Or(ast.Or, NeoAST): __slots__ = ()
class Param(ast.Param, NeoAST): __slots__ = ()
class Pass(ast.Pass, NeoAST): __slots__ = ()
class Pow(ast.Pow, NeoAST): __slots__ = ()
class RShift(ast.RShift, NeoAST): __slots__ = ()
class Raise(ast.Raise, NeoAST): __slots__ = ()
class Return(ast.Return, NeoAST): __slots__ = ()
class Set(ast.Set, NeoAST): __slots__ = ()
class SetComp(ast.SetComp, NeoAST): __slots__ = ()
class Slice(ast.Slice, NeoAST): __slots__ = ()
class Starred(ast.Starred, NeoAST): __slots__ = ()
class Store(ast.Store, NeoAST): __slots__ = ()
class Str(ast.Str, NeoAST): __slots__ = ()
class Sub(ast.Sub, NeoAST): __slots__ = ()
class Subscript(ast.Subscript, NeoAST): __slots__ = ()
class Suite(ast.Suite, NeoAST): __slots__ = ()
class Try(ast.Try, NeoAST): __slots__ = ()
class Tuple(ast.Tuple, NeoAST): __slots__ = ()
class TypeIgnore(ast.TypeIgnore, NeoAST): __slots__ = ()
class UAdd(ast.UAdd, NeoAST): __slots__ = ()
class USub(ast.USub, NeoAST): __slots__ = ()
class UnaryOp(ast.UnaryOp, NeoAST): __slots__ = ()
class While(ast.While, NeoAST): __slots__ = ()
class With(ast.With, NeoAST): __slots__ = ()
class Yield(ast.Yield, NeoAST): __slots__ = ()
class YieldFrom(ast.YieldFrom, NeoAST): __slots__ = ()
class alias(ast.alias, NeoAST): __slots__ = ()
class arg(ast.arg, NeoAST): __slots__ = ()
class arguments(ast.arguments, NeoAST): __slots__ = ()
class boolop(ast.boolop, NeoAST): __slots__ = ()
class cmpop(ast.cmpop, NeoAST): __slots__ = ()
class comprehension(ast.comprehension, NeoAST): __slots__ = ()
class excepthandler(ast.excepthandler, NeoAST): __slots__ = ()
class expr(ast.expr, NeoAST): __slots__ = ()
class expr_context(ast.expr_context, NeoAST): __slots__ = ()
class keyword(ast.keyword, NeoAST): __slots__ = ()
class match_case(ast.match_case, NeoAST): __slots__ = ()
class mod(ast.mod, NeoAST): __slots__ = ()
class operator(ast.operator, NeoAST): __slots__ = ()
class pattern(ast.pattern, NeoAST): __slots__ = ()
class slice(ast.slice, NeoAST): __slots__ = ()
class stmt(ast.stmt, NeoAST): __slots__ = ()
class type_ignore(ast.type_ignore, NeoAST): __slots__ = ()
class unaryop(ast.unaryop, NeoAST): __slots__ = ()
class withitem(ast.withitem, NeoAST): __slots__ = ()
# fmt: on


# FIXME a proper appraoch here is to use `sum type` feature to properly type this case.
# Reference: "Support for sealed classes" - https://mail.python.org/archives/list/typing-sig@python.org/thread/AKXUBJUUHBBKTLNIAFCA6HII5QQA2WFX/

if TYPE_CHECKING:
    Declaration = FunctionDef | AsyncFunctionDef | ClassDef
else:
    Declaration = (FunctionDef, AsyncFunctionDef, ClassDef)


Decoratable = Declaration
