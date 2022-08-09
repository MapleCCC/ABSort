from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from enum import Enum, auto
from functools import partial
from itertools import chain, combinations
from string import whitespace
from typing import TypeAlias, cast

import attrs
from more_itertools import flatten
from recipes.misc import profile
from recipes.operator import in_
from typing_extensions import assert_never

from .__version__ import __version__
from .ast_utils import Declaration, ast_get_source, ast_tree_edit_distance, ast_tree_size
from .cluster import chenyu
from .collections_extra import OrderedSet
from .directed_graph import DirectedGraph
from .utils import duplicated, ireverse, strict_splitlines
from .visitors import GetUndefinedVariableVisitor
from .weighted_graph import WeightedGraph


__all__ = [
    "absort_str",
    "FormatOption",
    "SortOrder",
    "NameRedefinition",
]


#
# Enumerations
#


class SortOrder(Enum):
    """ An enumeration to specify different kinds of sort order strategies """

    TOPOLOGICAL = auto()
    DEPTH_FIRST = auto()
    BREADTH_FIRST = auto()


#
# Type Annotations
#

PyVersion: TypeAlias = tuple[int, int]


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
    reverse: bool = False
    pin_main: bool = True
    aggressive: bool = True


#
# Routines
#


@profile
def absort_str(
    old_source: str,
    py_version: PyVersion = (3, 10),
    format_option: FormatOption = FormatOption(),
    sort_order: SortOrder = SortOrder.TOPOLOGICAL,
) -> str:
    """ Sort the source code in string """
    # TODO detail docstring. Specify exceptions raised under respective condition.

    def preliminary_sanity_check(top_level_stmts: list[ast.stmt]) -> None:
        # TODO add more sanity checks

        decls = [stmt for stmt in top_level_stmts if isinstance(stmt, Declaration)]
        decl_names = [decl.name for decl in decls]

        if duplicated(decl_names):
            raise NameRedefinition("Name redefinition exists. Not supported yet.")

    def post_sanity_check(old_source: str, new_source: str) -> None:

        # TODO purely functional multiset. persistent counter. persistent/frozen/immutable map/dict.
        # Take inspiration from clojure's builtin functions naming

        # Sanity check: only whitespace changes
        c1 = Counter(old_source)
        c2 = Counter(new_source)
        diff = set((c1 - c2) + (c2 - c1))
        assert diff <= set(whitespace), f"{diff=}"

    module_tree = ast.parse(old_source, feature_version=py_version)

    top_level_stmts = module_tree.body

    preliminary_sanity_check(top_level_stmts)

    blocks = find_continguous_decls(top_level_stmts)

    # Use strict_splitlines() instead of str.splitlines(), because CPython's ast.parse()
    # doesn't parse the source string "#\x0c0" as containing an expression.
    # TODO is't a bug of CPython? What's the behavior of PyPy? Open an issue?
    new_source_lines = strict_splitlines(old_source, keepends=True)

    # FIXME below lines are actually unnecessary at all

    offset = 0
    for lineno, end_lineno, decls in blocks:
        sorted_decls = absort_decls(decls, py_version, format_option, sort_order)
        related_source = get_related_source_of_block(
            old_source, sorted_decls, format_option
        )
        new_source_lines[lineno - 1 + offset : end_lineno + offset] = [related_source]
        offset -= end_lineno - lineno

    new_source = "".join(new_source_lines)

    # This line is a heuristic. It's visually bad to have blank lines at the
    # start and end of the document. So we explicitly remove them.
    new_source = new_source.strip()

    # Insert a final newline for POSIX compliant style.
    new_source = new_source + "\n"

    post_sanity_check(old_source, new_source)

    return new_source


# TODO Reuse more-itertools recipe to simplify

def find_continguous_decls(
    stmts: list[ast.stmt],
) -> Iterator[tuple[int, int, list[Declaration]]]:
    """ Yield blocks of continguous declarations """

    # WARNING: lineno and end_lineno are 1-indexed

    n = len(stmts)
    index = 0
    while index < n:
        while index < n and not isinstance(stmts[index], Declaration):
            index += 1

        if index == n:
            return

        start = index
        while index < n and isinstance(stmts[index], Declaration):
            index += 1
        end = index

        lineno = (cast(int, stmts[start - 1].end_lineno) + 1) if start else 1
        end_lineno = stmts[end - 1].end_lineno
        assert end_lineno is not None

        yield lineno, end_lineno, cast(list[Declaration], stmts[start:end])


@profile
def absort_decls(
    decls: Iterable[Declaration],
    py_version: PyVersion,
    format_option: FormatOption,
    sort_order: SortOrder,
) -> list[Declaration]:
    """ Sort a continguous block of declarations """

    def same_abstract_level_sorter(names: Iterable[str]) -> Iterator[str]:
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

        if format_option.aggressive:
            # Sort by putting two visually similar definitions together

            same_level_decls = [index[name] for name in names]
            sorted_decls = sort_decls_by_syntax_tree_similarity(same_level_decls)
            return (decl.name for decl in sorted_decls)

        else:
            return filter(in_(set(names)), decl_names)

    decls = list(decls)

    decl_names = [decl.name for decl in decls]
    if duplicated(decl_names):
        raise NameRedefinition("Name redefinition exists. Not supported yet.")

    index = {decl.name: decl for decl in decls}

    # TODO Use DGraph[Declaration] instead of DGraph[str]
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

    if format_option.pin_main and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    # Sanity check
    assert len(sorted_names) == len(decl_names) and set(sorted_names) == set(decl_names)

    return [index[name] for name in sorted_names]


@profile
def sort_decls_by_syntax_tree_similarity(
    decls: list[Declaration],
) -> Iterator[Declaration]:

    if len(decls) <= 1:
        return iter(decls)

    algorithm = "ZhangShasha"
    if any(ast_tree_size(decl) > 10 for decl in decls):
        algorithm = "PQGram"

    # Normalized PQGram distance and xxxxxxx has pseudo-metric properties. We can utilize this
    # property to reduce time complexity when sorting decls. e.g. no need to calculate all
    # n**2 distances.
    if len(decls) > 10:
        dist = partial(ast_tree_edit_distance, algorithm=algorithm)
        clusters = chenyu(decls, dist, k=3)
        return chain.from_iterable(clusters)

    graph: WeightedGraph[Declaration] = WeightedGraph()
    for decl1, decl2 in combinations(decls, 2):
        distance = ast_tree_edit_distance(decl1, decl2, algorithm)
        graph.add_edge(decl1, decl2, distance)
    return graph.minimum_spanning_tree()


@profile
def generate_dependency_graph(
    decls: Sequence[Declaration], py_version: PyVersion
) -> DirectedGraph[str]:
    """ Generate a dependency graph from a continguous block of declarations """

    # TODO return DGraph[Declaration] instead of DGraph[str]

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


def get_dependency_of_decl(decl: Declaration, py_version: PyVersion) -> set[str]:
    """ Calculate the dependencies (as set of symbols) of the declaration """

    temp_module = ast.Module(body=[decl], type_ignores=[])
    visitor = GetUndefinedVariableVisitor(py_version=py_version)
    return visitor.visit(temp_module)


def get_related_source_of_block(
    source: str,
    decls: list[Declaration],
    format_option: FormatOption,
) -> str:
    """ Retrieve source corresponding to the block of continguous declarations, from source """

    related_source = ""

    for decl in decls:

        decl_source = ast_get_source(source, decl)

        if format_option.aggressive:

            if not decl_source.strip():

                # FIXME this branch seems unreachable?
                # TODO Use git-blame to find the initial intention.

                # A heuristic. If only whitespaces are present, compress to two blank
                # lines. Because it's visually bad to have zero or too many blank lines
                # between two declarations. So we explicitly add it. Two blank lines
                # between declarations is conformant to the PEP-8 style (https://pep8.org/#blank-lines).
                decl_source = "\n\n"

            elif decl_source.splitlines()[0].strip():

                # FIXME str.strip() strips all whitespace characters. But some are
                # visible, like form feed character, e.g., source code in
                # `Lib/email/feedparser.py`. This fix is also applicable to
                # `str.strip()` across the whole source repo.

                # A heuristic. It's visually bad to have no blank lines between two
                # declarations. So we explicitly add it. Two blank lines between
                # declarations is conformant to the PEP-8 style (https://pep8.org/#blank-lines).
                decl_source = "\n\n" + decl_source

        related_source += decl_source

    return related_source
