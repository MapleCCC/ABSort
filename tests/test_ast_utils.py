import ast
from ast import Assign, Call, Constant, Expr, Load, Name, Store

from absort.ast_utils import ast_deep_equal, ast_tree_edit_distance


# TODO add property-based testing


def test_ast_equal() -> None:
    a = Name(id="print", ctx=Load())
    b = Name(id="print", ctx=Load())
    assert ast_deep_equal(a, b)

    a = Expr(
        value=Call(
            func=Name(id="print", ctx=Load()),
            args=[Constant(value="hello, world")],
            keywords=[],
        )
    )
    b = Expr(
        value=Call(
            func=Name(id="print", ctx=Load()),
            args=[Constant(value="hello, world")],
            keywords=[],
        )
    )
    assert ast_deep_equal(a, b)


def test_ast_tree_edit_distance() -> None:
    node1 = ast.parse("a=1")
    node2 = ast.parse("a=1")
    assert ast_tree_edit_distance(node1, node2) == 0
    node2 = ast.parse("b=1")
    assert ast_tree_edit_distance(node1, node2) == 1
    node2 = ast.parse("b=2")
    assert ast_tree_edit_distance(node1, node2) == 1.5
    node1 = Assign(
        targets=[Name(id="a", ctx=Store())],
        value=Constant(value=1, kind=None),
        type_comment=None,
    )
    node2 = Assign(
        targets=[Name(id="a", ctx=Store())],
        value=Constant(value=1, kind=None),
        type_comment=None,
    )
    assert ast_tree_edit_distance(node1, node2) == 0
    node1 = ast.parse("")
    node2 = ast.parse("")
    assert ast_tree_edit_distance(node1, node2) == 0
    node1 = ast.parse("a")
    node2 = ast.parse("a")
    assert ast_tree_edit_distance(node1, node2) == 0
    node1 = Expr(Name("a", Load()))
    node2 = Expr(Name("a", Load()))
    assert ast_tree_edit_distance(node1, node2) == 0
    node1 = Name("a", Load())
    node2 = Name("a", Load())
    assert ast_tree_edit_distance(node1, node2) == 0
