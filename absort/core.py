from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator, Sequence as Seq
from enum import Enum, auto
from functools import partial
from itertools import combinations
from string import whitespace
from typing import cast

import attrs
from more_itertools import flatten, one
from recipes.misc import profile
from typing_extensions import assert_never

from . import neoast as ast
from .__version__ import __version__
from .cluster import chenyu
from .collections_extra import OrderedSet
from .directed_graph import DirectedGraph as DGraph
from .neoast import Declaration
from .typing_extra import PyVersion
from .utils import char_diff, duplicated, ireverse, strict_splitlines
from .weighted_graph import WeightedGraph as WGraph


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
    py_version: PyVersion = sys.version_info[:2],
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
        # Sanity check: only whitespace changes are introduced.
        chars = set(char_diff(old_source, new_source))
        assert chars <= set(whitespace), f"{chars=}"

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

    def same_abstract_level_sorter(same_level_decls: Iterable[Declaration]) -> Iterator[Declaration]:
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
            return sort_decls_by_syntax_tree_similarity(same_level_decls)

        else:
            orders = {decl: idx for idx, decl in enumerate(decls)}
            return iter(sorted(same_level_decls, key=orders.__getitem__))

    decls = list(decls)

    if duplicated(decl.name for decl in decls):
        raise NameRedefinition("Name redefinition exists. Not supported yet.")

    # TODO Use DGraph[Declaration] instead of DGraph[str]
    graph = generate_dependency_graph(decls, py_version)

    # TODO Refactor

    if sort_order is SortOrder.TOPOLOGICAL:
        sccs = ireverse(graph.strongly_connected_components())
        sorted_decls = list(flatten(same_abstract_level_sorter(scc) for scc in sccs))

    elif sort_order in (SortOrder.DEPTH_FIRST, SortOrder.BREADTH_FIRST):

        if sort_order is SortOrder.DEPTH_FIRST:
            traverse_method = graph.dfs
        elif sort_order is SortOrder.BREADTH_FIRST:
            traverse_method = graph.bfs
        else:
            assert_never(sort_order)

        sources = list(graph.find_sources())
        num_src = len(sources)

        sorted_decls: list[Declaration]

        if num_src == 1:
            # 1. There is one entry point
            sorted_decls = list(traverse_method(sources[0]))

        elif num_src > 1:
            # 2. There are more than one entry points
            sorted_decls = []
            for src in sources:
                sorted_decls.extend(traverse_method(src))
            sorted_decls = list(OrderedSet(sorted_decls))

        else:
            sorted_decls = []

        remaining_decls = OrderedSet(decls) - sorted_decls
        sorted_decls.extend(same_abstract_level_sorter(remaining_decls))

    else:
        # Alternative: `typing.assert_never(sort_order)`
        raise ValueError

    if format_option.reverse:
        sorted_decls.reverse()

    if format_option.pin_main:
        main_decl = one(decl for decl in sorted_decls if decl.name == "main")
        sorted_decls.remove(main_decl)
        sorted_decls.append(main_decl)

    # Sanity check
    assert len(sorted_decls) == len(decls) and set(sorted_decls) == set(decls)

    return sorted_decls


@profile
def sort_decls_by_syntax_tree_similarity(
    decls: Iterable[Declaration],
) -> Iterator[Declaration]:

    decls = list(decls)

    if len(decls) <= 1:
        return iter(decls)

    algorithm = "ZhangShasha"
    if any(decl.size() > 10 for decl in decls):
        algorithm = "PQGram"

    # Normalized PQGram distance and xxxxxxx has pseudo-metric properties. We can utilize this
    # property to reduce time complexity when sorting decls. e.g. no need to calculate all
    # n**2 distances.
    if len(decls) > 10:
        dist = partial(ast.AST.edit_distance, algorithm=algorithm)
        clusters = chenyu(decls, dist, k=3)
        return flatten(clusters)

    graph = WGraph[Declaration]()
    for decl1, decl2 in combinations(decls, 2):
        distance = decl1.edit_distance(decl2, algorithm)
        graph.add_edge(decl1, decl2, distance)
    return graph.minimum_spanning_tree()


@profile
def generate_dependency_graph(
    decls: Seq[Declaration], py_version: PyVersion
) -> DGraph[Declaration]:
    """ Generate a dependency graph from a continguous block of declarations """

    # TODO return DGraph[Declaration] instead of DGraph[str]

    assert not duplicated(decl.name for decl in decls)

    index = {decl.name: decl for decl in decls}

    graph = DGraph[Declaration]()

    for decl in decls:
        deps = get_dependency_of_decl(decl, py_version)
        for dep in deps:

            # We don't add the dependency to the dependency graph, when:
            # 1. the dependency is not among the decls to sort;
            # 2. the dependency is of the same name with the decl itself. It can be inferred
            # that the dependency must come from other places, thus no need to add it to
            # the dependency graph anyway. One example: https://github.com/pytest-dev/py/blob/92e36e60b22e2520337748f950e3d885e0c7c551/py/_log/warning.py#L3
            if dep not in index or dep == decl.name:
                continue

            graph.add_edge(decl, index[dep])

        # Below line is necessary for adding node with zero out-degree to the graph.
        graph.add_node(decl)

    return graph


def get_dependency_of_decl(decl: Declaration, py_version: PyVersion) -> set[str]:
    """ Calculate the dependencies (as set of symbols) of the declaration """
    return decl.free_symbols(py_version)


def get_related_source_of_block(
    source: str,
    decls: list[Declaration],
    format_option: FormatOption,
) -> str:
    """ Retrieve source corresponding to the block of continguous declarations, from source """

    related_source = ""

    for decl in decls:

        decl_source = decl.source(source)

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
