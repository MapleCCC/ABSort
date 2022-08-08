import ast
import copy
import re
from collections.abc import Iterator
from functools import cache
from numbers import Number
from typing import TYPE_CHECKING, Literal, TypeAlias

from .treedist import pqgram, zhangshasha
from .utils import cached_splitlines, constantfunc, hamming_distance, iequal, ireverse


__all__ = [
    "Declaration",
    "Decoratable",
    "ast_pretty_dump",
    "ast_ordered_walk",
    "ast_strip_location_info",
    "ast_get_leading_comment_and_decorator_list_source_lines",
    "ast_get_leading_comment_source_lines",
    "ast_get_decorator_list_source_lines",
    "ast_get_source_lines",
    "cached_ast_iter_child_nodes",
    "ast_iter_non_node_fields",
    "fast_ast_iter_child_nodes",
    "ast_tree_edit_distance",
    "ast_shallow_equal",
    "ast_deep_equal",
    "ast_tree_size",
]


# TODO rewrite this whole module with libCST as drop-in replacement of the builtin ast module


def is_blank_line(line: str) -> bool:
    return not line.strip()

def is_comment_line(line: str) -> bool:
    return line.lstrip().startswith("#")


# FIXME a proper appraoch here is to use `sum type` feature to properly type this case.
# Reference: "Support for sealed classes" - https://mail.python.org/archives/list/typing-sig@python.org/thread/AKXUBJUUHBBKTLNIAFCA6HII5QQA2WFX/


if TYPE_CHECKING:
    Declaration = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
else:
    Declaration = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


Decoratable = Declaration


# With the advent of the `indent` keyword argument of `ast.parse()` since Python 3.9,
# `ast.pretty_dump()` is by and large supplanted.
def ast_pretty_dump(
    node: ast.AST, annotate_fields: bool = True, include_attributes: bool = False
) -> str:
    """ Use black formatting library to prettify the dumped AST """

    # TODO rewrite with libCST's utilites

    dumped = ast.dump(node, annotate_fields, include_attributes)

    try:
        import black  # type: ignore
        return black.format_str(dumped, mode=black.FileMode())
    except ImportError:
        raise RuntimeError(
            "Black is required to use ast_pretty_dump(). "
            "Try `python -m pip install -U black` to install."
        )
    except AttributeError:
        # TODO remove version incompatible check after black publishes the first
        # stable version.
        raise RuntimeError("black version incompatible")


def ast_ordered_walk(node: ast.AST) -> Iterator[ast.AST]:
    """ Depth-First Traversal of the AST """
    children = fast_ast_iter_child_nodes(node)
    for child in children:
        yield child
        yield from ast_ordered_walk(child)


def ast_strip_location_info(node: ast.AST, in_place: bool = True) -> ast.AST | None:
    """ Strip location info from AST nodes, recursively """

    if not in_place:
        new_node = copy.deepcopy(node)
        ast_strip_location_info(new_node, in_place=True)
        return new_node

    location_info_attrs = ("lineno", "col_offset", "end_lineno", "end_col_offset")
    for desc in ast_ordered_walk(node):
        for attr in location_info_attrs:
            try:
                delattr(desc, attr)
            except AttributeError:
                pass


def ast_get_leading_comment_and_decorator_list_source_lines(
    source: str, node: ast.AST
) -> list[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    # Use strict_splitlines() instead of str.splitlines(), because CPython's ast.parse()
    # doesn't parse the source string "#\x0c0" as containing an expression.
    above_lines = cached_splitlines(source, strict=True)[: node.lineno - 1]

    decorator_list_linenos: set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    boundary_lineno = 0  # 0 is a virtual line
    for lineno, line in ireverse(zip(range(1, node.lineno), above_lines)):
        if not (
            is_blank_line(line)
            or is_comment_line(line)
            or lineno in decorator_list_linenos
        ):
            boundary_lineno = lineno
            break

    leading_source_lines = above_lines[boundary_lineno : node.lineno - 1]

    return leading_source_lines


def ast_get_leading_comment_source_lines(source: str, node: ast.AST) -> list[str]:
    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    # Use strict_splitlines() instead of str.splitlines(), because CPython's ast.parse()
    # doesn't parse the source string "#\x0c0" as containing an expression.
    above_lines = cached_splitlines(source, strict=True)[: node.lineno - 1]

    decorator_list_linenos: set[int] = set()
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_linenos.update(range(lineno, end_lineno + 1))

    leading_comment_lines: list[str] = []
    for lineno, line in ireverse(zip(range(1, node.lineno), above_lines)):
        if lineno in decorator_list_linenos:
            continue
        elif is_blank_line(line) or is_comment_line(line):
            leading_comment_lines.append(line)
        else:
            break

    leading_comment_lines.reverse()
    return leading_comment_lines


def ast_get_decorator_list_source_lines(source: str, node: ast.AST) -> list[str]:
    """
    Return source lines of the decorator list that decorate a function/class as given
    by the node argument.
    """

    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    # Use strict_splitlines() instead of str.splitlines(), because CPython's ast.parse()
    # doesn't parse the source string "#\x0c0" as containing an expression.
    source_lines = cached_splitlines(source, strict=True)

    decorator_list_lines = []
    for decorator in getattr(node, "decorator_list", []):
        lineno, end_lineno = decorator.lineno, decorator.end_lineno
        decorator_list_lines.extend(source_lines[lineno - 1 : end_lineno])

    return decorator_list_lines


def ast_get_source_lines(source: str, node: ast.AST) -> list[str]:
    """ Retrieve source lines corresponding to the AST node, from the source """

    # XXX the `linecache` stdlib module

    # WARNING: ast.AST.lineno and ast.AST.end_lineno are 1-indexed

    # Use strict_splitlines() instead of str.splitlines(), because CPython's ast.parse()
    # doesn't parse the source string "#\x0c0" as containing an expression.
    whole_source_lines = cached_splitlines(source, strict=True)

    lineno, end_lineno = node.lineno, node.end_lineno
    source_lines = whole_source_lines[lineno - 1 : end_lineno]

    return source_lines


# XXX Is cached_ast_iter_child_nodes usable across the whole source repository?
@cache
def cached_ast_iter_child_nodes(node: ast.AST) -> list[ast.AST]:
    """ A cached version of the `fast_ast_iter_child_nodes` method """
    return list(fast_ast_iter_child_nodes(node))


class DeprecatedASTNodeError(Exception):
    """ An exception to signal that some AST node is deprecated """


Field: TypeAlias = tuple[str, str]
Fields: TypeAlias = tuple[Field, ...]


def retrieve_ast_node_class_fields(
    ast_node_class: type[ast.AST],
) -> Fields:  # pragma: no cover
    if ast_node_class is ast.AST:
        raise ValueError("Abstract node class has no fields")

    doc = ast_node_class.__doc__
    assert doc

    if re.fullmatch(r"Deprecated AST node class\..*", doc):
        raise DeprecatedASTNodeError(
            f"The ast node class {ast_node_class} is deprecated"
        )

    concrete_class_doc_pattern = r"\w+(?: = )?(?:\((?:\w+[?*]? \w+, )*\w+[?*]? \w+\))?"
    concrete_class_doc_pattern_with_name_group = (
        r"\w+(?: = )?(?:\((?P<attributes>(?:\w+[?*]? \w+, )*\w+[?*]? \w+)\))?"
    )
    abstract_class_doc_pattern = (
        r"\w+ = ("
        + concrete_class_doc_pattern
        + r"\s*\|\s*)*"
        + concrete_class_doc_pattern
    )

    if re.fullmatch(abstract_class_doc_pattern, doc):
        raise ValueError("Abstract node class has no fields")

    m = re.fullmatch(concrete_class_doc_pattern_with_name_group, doc)
    assert m, f"{ast_node_class} can't match"

    attributes = m.group("attributes")

    if attributes is None:
        # Example: ast.Load, ast.Store, ast.Del, etc.
        return ()

    return tuple(tuple(attr.split()) for attr in attributes.split(","))


def all_ast_node_classes() -> Iterator[tuple[str, type[ast.AST]]]:  # pragma: no cover
    # FIXME dir() is meant for interactive usage.
    for name in dir(ast):
        attr = getattr(ast, name)
        try:
            if issubclass(attr, ast.AST):
                attr_name = str(attr)
                m = re.fullmatch(r"<class 'ast.(?P<class_name>.*)'>", attr_name)
                assert m is not None
                yield m.group("class_name"), attr
        except TypeError:
            pass


def build_ast_node_class_fields_table() -> dict[str, Fields]:  # pragma: no cover
    table: dict[str, Fields] = {}
    for name, cls in all_ast_node_classes():
        try:
            fields = retrieve_ast_node_class_fields(cls)
        except (DeprecatedASTNodeError, ValueError):
            continue
        table[name] = fields
    return table


# The table is automatically built by calling the function build_ast_node_class_fields_table(),
# as it will be too tedious to manually build and maintain the table.
ast_node_class_fields_table = {
    "Add": (),
    "And": (),
    "AnnAssign": (
        ("expr", "target"),
        ("expr", "annotation"),
        ("expr?", "value"),
        ("int", "simple"),
    ),
    "Assert": (("expr", "test"), ("expr?", "msg")),
    "Assign": (("expr*", "targets"), ("expr", "value"), ("string?", "type_comment")),
    "AsyncFor": (
        ("expr", "target"),
        ("expr", "iter"),
        ("stmt*", "body"),
        ("stmt*", "orelse"),
        ("string?", "type_comment"),
    ),
    "AsyncFunctionDef": (
        ("identifier", "name"),
        ("arguments", "args"),
        ("stmt*", "body"),
        ("expr*", "decorator_list"),
        ("expr?", "returns"),
        ("string?", "type_comment"),
    ),
    "AsyncWith": (
        ("withitem*", "items"),
        ("stmt*", "body"),
        ("string?", "type_comment"),
    ),
    "Attribute": (("expr", "value"), ("identifier", "attr"), ("expr_context", "ctx")),
    "AugAssign": (("expr", "target"), ("operator", "op"), ("expr", "value")),
    "Await": (("expr", "value"),),
    "BinOp": (("expr", "left"), ("operator", "op"), ("expr", "right")),
    "BitAnd": (),
    "BitOr": (),
    "BitXor": (),
    "BoolOp": (("boolop", "op"), ("expr*", "values")),
    "Break": (),
    "Call": (("expr", "func"), ("expr*", "args"), ("keyword*", "keywords")),
    "ClassDef": (
        ("identifier", "name"),
        ("expr*", "bases"),
        ("keyword*", "keywords"),
        ("stmt*", "body"),
        ("expr*", "decorator_list"),
    ),
    "Compare": (("expr", "left"), ("cmpop*", "ops"), ("expr*", "comparators")),
    "Constant": (("constant", "value"), ("string?", "kind")),
    "Continue": (),
    "Del": (),
    "Delete": (("expr*", "targets"),),
    "Dict": (("expr*", "keys"), ("expr*", "values")),
    "DictComp": (("expr", "key"), ("expr", "value"), ("comprehension*", "generators")),
    "Div": (),
    "Eq": (),
    "ExceptHandler": (("expr?", "type"), ("identifier?", "name"), ("stmt*", "body")),
    "Expr": (("expr", "value"),),
    "Expression": (("expr", "body"),),
    "FloorDiv": (),
    "For": (
        ("expr", "target"),
        ("expr", "iter"),
        ("stmt*", "body"),
        ("stmt*", "orelse"),
        ("string?", "type_comment"),
    ),
    "FormattedValue": (
        ("expr", "value"),
        ("int?", "conversion"),
        ("expr?", "format_spec"),
    ),
    "FunctionDef": (
        ("identifier", "name"),
        ("arguments", "args"),
        ("stmt*", "body"),
        ("expr*", "decorator_list"),
        ("expr?", "returns"),
        ("string?", "type_comment"),
    ),
    "FunctionType": (("expr*", "argtypes"), ("expr", "returns")),
    "GeneratorExp": (("expr", "elt"), ("comprehension*", "generators")),
    "Global": (("identifier*", "names"),),
    "Gt": (),
    "GtE": (),
    "If": (("expr", "test"), ("stmt*", "body"), ("stmt*", "orelse")),
    "IfExp": (("expr", "test"), ("expr", "body"), ("expr", "orelse")),
    "Import": (("alias*", "names"),),
    "ImportFrom": (("identifier?", "module"), ("alias*", "names"), ("int?", "level")),
    "In": (),
    "Interactive": (("stmt*", "body"),),
    "Invert": (),
    "Is": (),
    "IsNot": (),
    "JoinedStr": (("expr*", "values"),),
    "LShift": (),
    "Lambda": (("arguments", "args"), ("expr", "body")),
    "List": (("expr*", "elts"), ("expr_context", "ctx")),
    "ListComp": (("expr", "elt"), ("comprehension*", "generators")),
    "Load": (),
    "Lt": (),
    "LtE": (),
    "MatMult": (),
    "Mod": (),
    "Module": (("stmt*", "body"), ("type_ignore*", "type_ignores")),
    "Mult": (),
    "Name": (("identifier", "id"), ("expr_context", "ctx")),
    "NamedExpr": (("expr", "target"), ("expr", "value")),
    "Nonlocal": (("identifier*", "names"),),
    "Not": (),
    "NotEq": (),
    "NotIn": (),
    "Or": (),
    "Pass": (),
    "Pow": (),
    "RShift": (),
    "Raise": (("expr?", "exc"), ("expr?", "cause")),
    "Return": (("expr?", "value"),),
    "Set": (("expr*", "elts"),),
    "SetComp": (("expr", "elt"), ("comprehension*", "generators")),
    "Slice": (("expr?", "lower"), ("expr?", "upper"), ("expr?", "step")),
    "Starred": (("expr", "value"), ("expr_context", "ctx")),
    "Store": (),
    "Sub": (),
    "Subscript": (("expr", "value"), ("expr", "slice"), ("expr_context", "ctx")),
    "Try": (
        ("stmt*", "body"),
        ("excepthandler*", "handlers"),
        ("stmt*", "orelse"),
        ("stmt*", "finalbody"),
    ),
    "Tuple": (("expr*", "elts"), ("expr_context", "ctx")),
    "TypeIgnore": (("int", "lineno"), ("string", "tag")),
    "UAdd": (),
    "USub": (),
    "UnaryOp": (("unaryop", "op"), ("expr", "operand")),
    "While": (("expr", "test"), ("stmt*", "body"), ("stmt*", "orelse")),
    "With": (("withitem*", "items"), ("stmt*", "body"), ("string?", "type_comment")),
    "Yield": (("expr?", "value"),),
    "YieldFrom": (("expr", "value"),),
    "alias": (("identifier", "name"), ("identifier?", "asname")),
    "arg": (
        ("identifier", "arg"),
        ("expr?", "annotation"),
        ("string?", "type_comment"),
    ),
    "arguments": (
        ("arg*", "posonlyargs"),
        ("arg*", "args"),
        ("arg?", "vararg"),
        ("arg*", "kwonlyargs"),
        ("expr*", "kw_defaults"),
        ("arg?", "kwarg"),
        ("expr*", "defaults"),
    ),
    "comprehension": (
        ("expr", "target"),
        ("expr", "iter"),
        ("expr*", "ifs"),
        ("int", "is_async"),
    ),
    "keyword": (("identifier?", "arg"), ("expr", "value")),
    "withitem": (("expr", "context_expr"), ("expr?", "optional_vars")),
}


# Reference: https://docs.python.org/3/library/ast.html#abstract-grammar
Terminals = ("identifier", "int", "string", "constant")
# Reference: https://docs.python.org/3/library/ast.html#ast.Constant
TerminalType: TypeAlias = str | Number | None | tuple | frozenset


def ast_iter_non_node_fields(
    node: ast.AST,
) -> Iterator[TerminalType | list[TerminalType] | None]:
    """ Complement of the ast.iter_child_nodes function """

    class_name = node.__class__.__name__
    for type, name in ast_node_class_fields_table[class_name]:
        if type.rstrip("?*") in Terminals:
            yield getattr(node, name)


# TODO Benchmark to check if it is really faster than the builtin ast.iter_child_nodes


def fast_ast_iter_child_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """ Faster version of ast.iter_child_nodes """

    class_name = node.__class__.__name__
    for type, name in ast_node_class_fields_table[class_name]:
        if type.rstrip("?*") not in Terminals:
            attr = getattr(node, name)

            if type[-1] == "?":
                if attr is not None:
                    yield attr

            elif type[-1] == "*":

                # Edge case 1: dict unpacking
                #
                # Reference:
                #   "When doing dictionary unpacking using dictionary literals the
                #   expression to be expanded goes in the values list, with a None at
                #   the corresponding position in keys."
                #   - from https://docs.python.org/3/library/ast.html#ast.Dict
                if class_name == "Dict" and name == "keys":
                    # Or use filter()
                    yield from (expr for expr in attr if expr is not None)
                    continue

                # TODO search: What is required keyword argument default? ast official
                # doc has example.

                # Edge case 2: required keyword argument default
                #
                # Reference:
                #   "kw_defaults is a list of default values for keyword-only arguments.
                #   If one is None, the corresponding argument is required."
                #   - from https://docs.python.org/3/library/ast.html#ast.arguments
                if class_name == "arguments" and name == "kw_defaults":
                    # Or use filter()
                    yield from (expr for expr in attr if expr is not None)
                    continue

                # XXX maybe we can simply just "if not None, yield", and no that much
                # trouble.

                # FIXME we should substitue None with a bogus AST node, instead of just
                # deleting it. It's relevant when comparing children in
                # `ast_shadow_equal()` / `ast_deep_equal()`.

                # Uncomment below lines to activate debug mode
                # if None in attr:
                #     print(class_name, type, name, attr)

                yield from attr

            else:

                # Uncomment below lines to activate debug mode
                # if attr is None:
                #     print(class_name, type, name, attr)

                yield attr


def ast_tree_edit_distance(
    node1: ast.AST,
    node2: ast.AST,
    algorithm: Literal["ZhangShasha", "PQGram"] = "ZhangShasha"
) -> float:
    """
    Implementation is Zhang-Shasha's tree edit distance algorithm.

    Reference: https://epubs.siam.org/doi/abs/10.1137/0218082

    Optionally, specify the algorithm argument as "PQGram" to switch to PQGram tree edit
    distance algorithm, which is far more efficient for large trees.

    Note that the rename_cost function **should** return 0 for identical nodes.
    """

    # Note: one important thing to note here is that, `ast.AST() != ast.AST()`, namely,
    # ast.AST has no well-defined equality/identity.

    if algorithm == "ZhangShasha":
        # hopefully a sane default
        def rename_cost(node1: ast.AST, node2: ast.AST) -> float:
            return 1 - ast_shallow_equal(node1, node2)

        return zhangshasha(
            node1,
            node2,
            children=fast_ast_iter_child_nodes,
            insert_cost=constantfunc(1),
            delete_cost=constantfunc(1),
            rename_cost=rename_cost,
        )

    elif algorithm == "PQGram":
        # TODO Right now node type equality is used. Finer grained equality is called for.
        return pqgram(node1, node2, children=fast_ast_iter_child_nodes, label=type)

    else:
        raise ValueError("Invalid value for the algorithm argument")


def ast_shallow_equal(node1: ast.AST, node2: ast.AST) -> float:
    """
    Return equality of two ast nodes, by comparing shallow level data.
    Return zero if non-equal, and positive numbers if partial equal or complete equal.

    For advanced usage, the returned positive number is acutally a fraction between 0
    and 1, denoting the equality degree of the two nodes. The closer to 1 the more
    equal, and vice versa.
    """

    if type(node1) != type(node2):
        return 0

    fields1 = list(ast_iter_non_node_fields(node1))
    fields2 = list(ast_iter_non_node_fields(node2))
    assert len(fields1) == len(fields2)
    num_fields = len(fields1)
    if num_fields == 0:
        return 1
    return 1 - (hamming_distance(fields1, fields2) / num_fields)


def ast_deep_equal(node1: ast.AST, node2: ast.AST) -> bool:
    """ Return if two ast nodes are semantically equal """

    # TODO rewrite with libCST's deep_equals()

    if type(node1) != type(node2):
        return False

    if list(ast_iter_non_node_fields(node1)) != list(ast_iter_non_node_fields(node2)):
        return False

    return iequal(
        fast_ast_iter_child_nodes(node1),
        fast_ast_iter_child_nodes(node2),
        equal=ast_deep_equal,
        strict=True,
    )


def ast_tree_size(node: ast.AST) -> int:
    return 1 + sum(map(ast_tree_size, fast_ast_iter_child_nodes(node)))
