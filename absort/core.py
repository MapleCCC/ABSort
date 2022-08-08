import ast
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from enum import Enum, auto
from functools import partial
from itertools import chain, combinations
from string import whitespace
from typing import cast

import attrs
from more_itertools import first_true, flatten
from typing_extensions import assert_never

from .__version__ import __version__
from .ast_utils import (
    ast_get_decorator_list_source_lines,
    ast_get_leading_comment_and_decorator_list_source_lines,
    ast_get_leading_comment_source_lines,
    ast_get_source_lines,
    ast_tree_edit_distance,
    ast_tree_size,
)
from .cluster import chenyu
from .collections_extra import OrderedSet
from .directed_graph import DirectedGraph
from .typing_extra import Declaration, DeclarationType
from .utils import (
    duplicated,
    identityfunc,
    ireverse,
    strict_splitlines,
    whitespace_lines,
)
from .visitors import GetUndefinedVariableVisitor
from .weighted_graph import WeightedGraph


__all__ = [
    "absort_str",
    "CommentStrategy",
    "FormatOption",
    "SortOrder",
    "NameRedefinition",
]


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = identityfunc


#
# Enumerations
#


class CommentStrategy(Enum):
    """ An enumeration to specify different kinds of comment strategies """

    PUSH_TOP = "push-top"
    ATTR_FOLLOW_DECL = "attr-follow-decl"
    IGNORE = "ignore"


class SortOrder(Enum):
    """ An enumeration to specify different kinds of sort order strategies """

    TOPOLOGICAL = auto()
    DEPTH_FIRST = auto()
    BREADTH_FIRST = auto()


#
# Type Annotations
#

PyVersion = tuple[int, int]


#
# Custom Exceptions
#


# Alternative name: DuplicateNames
class NameRedefinition(Exception):
    """ An exception to signal that duplicate name definitions are detected """


#
# Utility Classes
#


@attrs.frozen
class FormatOption:
    no_aggressive: bool = False
    reverse: bool = False
    no_fix_main_to_bottom: bool = False
    separate_class_and_function: bool = False


#
# Routines
#


@profile  # type: ignore
def absort_str(
    old_source: str,
    py_version: PyVersion = (3, 10),
    comment_strategy: CommentStrategy = CommentStrategy.ATTR_FOLLOW_DECL,
    format_option: FormatOption = FormatOption(),
    sort_order: SortOrder = SortOrder.TOPOLOGICAL,
) -> str:
    """ Sort the source code in string """

    def preliminary_sanity_check(top_level_stmts: list[ast.stmt]) -> None:
        # TODO add more sanity checks

        decls = [stmt for stmt in top_level_stmts if isinstance(stmt, Declaration)]
        decl_names = [decl.name for decl in decls]

        if duplicated(decl_names):
            raise NameRedefinition("Name redefinition exists. Not supported yet.")

    module_tree = ast.parse(old_source, feature_version=py_version)

    top_level_stmts = module_tree.body

    preliminary_sanity_check(top_level_stmts)

    blocks = find_continguous_decls(top_level_stmts)

    # Use strict_splitlines() instead of str.splitlines(), because CPython's ast.parse()
    # doesn't parse the source string "#\x0c0" as containing an expression.
    # TODO is't a bug of CPython? What's the behavior of PyPy? Open an issue?
    new_source_lines = strict_splitlines(old_source)

    # FIXME below lines are actually unnecessary at all

    offset = 0
    for lineno, end_lineno, decls in blocks:
        sorted_decls = list(absort_decls(decls, py_version, format_option, sort_order))
        source_lines = get_related_source_lines_of_block(
            old_source, sorted_decls, comment_strategy, format_option
        )
        new_source_lines[lineno - 1 + offset : end_lineno + offset] = source_lines
        offset += len(source_lines) - (end_lineno - lineno + 1)

    new_source = "\n".join(new_source_lines) + "\n"

    # This line is a heuristic. It's visually bad to have blank lines at the
    # start of the document. So we explicitly remove them.
    new_source = new_source.lstrip()

    # TODO purely functional multiset. persistent counter. persistent/frozen/immutable map/dict.
    # Take inspiration from clojure's builtin functions naming

    # Sanity check: only whitespace changes
    diff = Counter(new_source)
    # Shouldn't use the `-` subtraction operator, because it automatically discards
    # non-positive counts. This side effect is undesirable here.
    diff.subtract(Counter(old_source))
    diff_chars = set(diff)
    assert diff_chars <= set(whitespace)

    return new_source


# TODO Reuse more-itertools recipe to simplify

def find_continguous_decls(
    stmts: list[ast.stmt],
) -> Iterator[tuple[int, int, list[DeclarationType]]]:
    """ Yield blocks of continguous declarations """

    # WARNING: lineno and end_lineno are 1-indexed

    n = len(stmts)
    index = 0
    while index < n:
        while index < n and not isinstance(stmts[index], Declaration):
            index += 1

        if index == n - 1:
            return

        start = index
        while index < n and isinstance(stmts[index], Declaration):
            index += 1
        end = index

        lineno = cast(int, stmts[start - 1].end_lineno) + 1
        end_lineno = stmts[end - 1].end_lineno
        assert end_lineno is not None

        yield lineno, end_lineno, cast(list[DeclarationType], stmts[start:end])


@profile  # type: ignore
def absort_decls(
    decls: Iterable[DeclarationType],
    py_version: PyVersion,
    format_option: FormatOption,
    sort_order: SortOrder,
) -> Iterator[DeclarationType]:
    """ Sort a continguous block of declarations """

    def same_abstract_level_sorter(names: Iterable[str]) -> Iterable[str]:
        """ Specify how to sort declarations within the same abstract level """

        # If the `--no-aggressive` option is set, sort by retaining their original relative
        # order, to reduce diff size.
        #
        # Otherwise, sort by code similarity.
        #
        # Possible alternatives: sort by lexicographical order of the names, sort by body
        # size, sort by name length, etc.
        #
        # TODO More advanced option is to utilize power of machine learning to put two
        # visually/semantically similar function/class definitions near each other.
        #
        # Code similarity can be implemented in:
        # 1. easy and naive way: source code string similarity. E.g., shortest edit distance algorithm.
        # 2. sophisticated way: syntax tree similarity. E.g., the classic Zhange-Shaha algorithm.

        if format_option.no_aggressive:
            decl_name_inverse_index = {name: idx for idx, name in enumerate(decl_names)}
            return sorted(names, key=lambda name: decl_name_inverse_index[name])

        else:
            # Sort by putting two visually similar definitions together

            name_lookup_table = {decl.name: decl for decl in decls}
            same_level_decls = [name_lookup_table[name] for name in names]
            sorted_decls = sort_decls_by_syntax_tree_similarity(same_level_decls)
            return (decl.name for decl in sorted_decls)

    decls = list(decls)

    if format_option.separate_class_and_function:
        class_decls = [decl for decl in decls if isinstance(decl, ast.ClassDef)]
        func_decls = [
            decl
            for decl in decls
            if isinstance(decl, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if class_decls and func_decls:
            yield from absort_decls(class_decls, py_version, format_option, sort_order)
            yield from absort_decls(func_decls, py_version, format_option, sort_order)
            return

    decl_names = [decl.name for decl in decls]
    if duplicated(decl_names):
        raise NameRedefinition("Name redefinition exists. Not supported yet.")

    graph = generate_dependency_graph(decls, py_version)

    # TODO Refactor

    if sort_order is SortOrder.TOPOLOGICAL:
        sccs = ireverse(graph.strongly_connected_components())
        sorted_names = list(flatten(same_abstract_level_sorter(scc) for scc in sccs))

    elif sort_order in (SortOrder.DEPTH_FIRST, SortOrder.BREADTH_FIRST):

        if sort_order is SortOrder.DEPTH_FIRST:
            traverse_method = graph.dfs
        elif sort_order is SortOrder.BREADTH_FIRST:
            traverse_method = graph.bfs
        else:
            assert_never(sort_order)

        sources = list(graph.find_sources())
        num_src = len(sources)

        if num_src == 1:
            # 1. There is one entry point
            sorted_names = list(traverse_method(sources[0]))

        elif num_src > 1:
            # 2. There are more than one entry points
            sorted_names = []
            for src in sources:
                sorted_names.extend(traverse_method(src))
            sorted_names = list(OrderedSet(sorted_names))

        else:
            sorted_names = []

        remaining_names = OrderedSet(decl_names) - sorted_names
        sorted_names.extend(same_abstract_level_sorter(remaining_names))

    else:
        # Alternative: `typing.assert_never(sort_order)`
        raise ValueError

    if format_option.reverse:
        sorted_names.reverse()

    if not format_option.no_fix_main_to_bottom and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    # Sanity check
    assert len(sorted_names) == len(decl_names) and set(sorted_names) == set(decl_names)

    # There is always one, and only one, decl that matches the name, we use
    # short-circuit to optimize.
    for name in sorted_names:
        name_matcher = lambda decl: decl.name == name
        yield cast(DeclarationType, first_true(decls, pred=name_matcher))


def sort_decls_by_syntax_tree_similarity(
    decls: list[DeclarationType],
) -> Iterator[DeclarationType]:

    if len(decls) <= 1:
        return iter(decls)

    algorithm = "ZhangShasha"
    if any(ast_tree_size(decl) > 10 for decl in decls):
        algorithm = "PQGram"

    # Normalized PQGram distance and xxxxxxx has pseudo-metric properties. We can utilize this
    # property to reduce time complexity when sorting decls. e.g. no need to calculate all
    # n**2 distances.
    if len(decls) > 10:
        _ast_tree_edit_distance = partial(ast_tree_edit_distance, algorithm=algorithm)
        clusters = chenyu(decls, _ast_tree_edit_distance, k=3)
        return chain.from_iterable(clusters)

    graph: WeightedGraph[DeclarationType] = WeightedGraph()
    for decl1, decl2 in combinations(decls, 2):
        distance = ast_tree_edit_distance(decl1, decl2, algorithm)
        graph.add_edge(decl1, decl2, distance)
    return graph.minimum_spanning_tree()


def generate_dependency_graph(
    decls: Sequence[DeclarationType], py_version: PyVersion
) -> DirectedGraph[str]:
    """ Generate a dependency graph from a continguous block of declarations """

    # TODO return DGraph[DeclarationType] instead of DGraph[str]

    decl_names = [decl.name for decl in decls]

    graph: DirectedGraph[str] = DirectedGraph()

    for decl in decls:
        deps = get_dependency_of_decl(decl, py_version)
        for dep in deps:

            # We don't add the dependency to the dependency graph, when:
            # 1. the dependency is not among the decls to sort;
            # 2. the dependency is of the same name with the decl itself. It can be inferred
            # that the dependency must come from other places, thus no need to add it to
            # the dependency graph anyway. One example: https://github.com/pytest-dev/py/blob/92e36e60b22e2520337748f950e3d885e0c7c551/py/_log/warning.py#L3
            if dep not in decl_names or dep == decl.name:
                continue

            graph.add_edge(decl.name, dep)

        # Below line is necessary for adding node with zero out-degree to the graph.
        graph.add_node(decl.name)

    return graph


def get_dependency_of_decl(decl: DeclarationType, py_version: PyVersion) -> set[str]:
    """ Calculate the dependencies (as set of symbols) of the declaration """

    temp_module = ast.Module(body=[decl], type_ignores=[])
    visitor = GetUndefinedVariableVisitor(py_version=py_version)
    return visitor.visit(temp_module)


def get_related_source_lines_of_block(
    source: str,
    decls: list[DeclarationType],
    comment_strategy: CommentStrategy,
    format_option: FormatOption,
) -> list[str]:
    """ Retrieve source lines corresponding to the block of continguous declarations, from source """

    source_lines = []

    for decl in decls:

        related_source_lines = get_related_source_lines_of_decl(
            source, decl, comment_strategy
        )

        if format_option.no_aggressive:
            source_lines += related_source_lines
        elif whitespace_lines(related_source_lines):

            # FIXME this branch seems unreachable?
            # TODO Use git-blame to find the initial intention.

            # A heuristic. If only whitespaces are present, compress to two blank lines.
            # Because it's visually bad to have zero or too many blank lines between
            # two declarations. So we explicitly add it. Two blank lines between
            # declarations is PEP8 style (https://pep8.org/#blank-lines)
            source_lines += "\n\n".splitlines()

        elif related_source_lines[0].strip():

            # FIXME str.strip() strips all whitespace characters. But some are visible,
            # like form feed character, e.g. source code in Lib/email/feedparser.py
            # This fix also applies to str.strip() across the whole repository

            # A heuristic. It's visually bad to have no blank lines
            # between two declarations. So we explicitly add it. Two blank lines between
            # declarations is PEP8 style (https://pep8.org/#blank-lines)
            source_lines += "\n\n".splitlines() + related_source_lines

        else:
            source_lines += related_source_lines

    if comment_strategy is CommentStrategy.PUSH_TOP:
        total_comment_lines = []
        for decl in decls:
            comment_lines = ast_get_leading_comment_source_lines(source, decl)

            # A heuristic to return empty result if only whitespaces are present
            if not whitespace_lines(comment_lines):
                total_comment_lines += comment_lines

        source_lines = total_comment_lines + source_lines

    return source_lines


def get_related_source_lines_of_decl(
    source: str, node: ast.AST, comment_strategy: CommentStrategy
) -> list[str]:
    """ Retrieve source lines corresponding to the AST node, from the source """

    source_lines = []

    if comment_strategy is CommentStrategy.ATTR_FOLLOW_DECL:
        source_lines += ast_get_leading_comment_and_decorator_list_source_lines(
            source, node
        )
    elif comment_strategy in (CommentStrategy.PUSH_TOP, CommentStrategy.IGNORE):
        source_lines += ast_get_decorator_list_source_lines(source, node)
    else:
        # Alternative: `typing.assert_never(comment_strategy)`
        raise ValueError

    source_lines += ast_get_source_lines(source, node)

    return source_lines
