#!/usr/bin/env python3

from __future__ import annotations

import ast
import asyncio
import contextlib
import re
import sys
from collections import Counter
from collections.abc import AsyncIterator, Iterable, Iterator, Sequence
from datetime import datetime
from enum import Enum
from functools import partial
from itertools import chain, combinations
from operator import itemgetter
from types import SimpleNamespace
from typing import Any

import attr
import cchardet
import click
from colorama import colorama_text
from more_itertools import first_true

from .__version__ import __version__
from .aiopathlib import AsyncPath as Path
from .ast_utils import (
    ast_get_decorator_list_source_lines,
    ast_get_leading_comment_and_decorator_list_source_lines,
    ast_get_leading_comment_source_lines,
    ast_get_source_lines,
    ast_tree_edit_distance,
    ast_tree_size,
)
from .async_utils import run_in_event_loop
from .collections_extra import OrderedSet
from .directed_graph import DirectedGraph
from .exceptions import Unreachable
from .typing_extra import Declaration, DeclarationType
from .utils import (
    bright_green,
    bright_yellow,
    chenyu,
    colored_unified_diff,
    duplicated,
    identityfunc,
    ireverse,
    no_color_context,
    silent_context,
    strict_splitlines,
    whitespace_lines,
)
from .visitors import GetUndefinedVariableVisitor
from .weighted_graph import WeightedGraph


__all__ = [
    "absort_str",
    "absort_file",
    "absort_files",
    "CommentStrategy",
    "FormatOption",
    "FileAction",
    "SortOrder",
    "NameRedefinition",
]


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = identityfunc


# Optionally use uvloop to boost speed
try:
    import uvloop  # type: ignore

    uvloop.install()
except ImportError:
    pass


#
# Enumerations
#


class FileAction(Enum):
    """ An enumeration to specify different kinds of file actions """

    CHECK = 0
    DIFF = 1
    PRINT = 2
    WRITE = 3


class CommentStrategy(Enum):
    """ An enumeration to specify different kinds of comment strategies """

    PUSH_TOP = "push-top"
    ATTR_FOLLOW_DECL = "attr-follow-decl"
    IGNORE = "ignore"


class SortOrder(Enum):
    """"""

    TOPOLOGICAL = 0
    DEPTH_FIRST = 1
    BREADTH_FIRST = 2


#
# Constants
#

# Specify the location of the cache directory
CACHE_DIR = Path.sync_home() / ".absort_cache"
# Specify the maximum size threshold fot the cache directory (in bytes)
CACHE_MAX_SIZE = 400000  # unit is byte

#
# Types
#

PyVersion = tuple[int, int]

#
# Global Variables
#

#
# Custom Exceptions
#

# Alternative name: DuplicateNames
class NameRedefinition(Exception):
    """ An exception to signal that duplicate name definitions are detected """


class ABSortFail(Exception):
    """ An exception to signal that sorting fails """


#
# Utility Classes
#


@attr.s(auto_attribs=True, slots=True)
class Digest:
    """ A semantic data class to represent digest data """

    unmodified: int = 0
    modified: int = 0
    failed: int = 0

    def __getitem__(self, key: str) -> int:
        return attr.asdict(self)[key]

    def __add__(self, other: Any) -> Digest:
        if not isinstance(other, Digest):
            return NotImplemented
        c1 = Counter(attr.asdict(self))
        c2 = Counter(attr.asdict(other))
        return Digest(**(c1 + c2))  # type: ignore


@attr.s(auto_attribs=True, frozen=True)
class FormatOption:
    no_aggressive: bool = False
    reverse: bool = False
    no_fix_main_to_bottom: bool = False
    separate_class_and_function: bool = False


class CommentStrategyParamType(click.ParamType):
    """ A parameter type for the --comment-strategy CLI option """

    name = "comment_strategy"

    def convert(self, value: str, param: Any, ctx: Any) -> CommentStrategy:
        try:
            return CommentStrategy(value)

        except ValueError:
            self.fail(
                "--comment-strategy argument has invalid value. "
                "Possible values are `push-top`, `attr-follow-decl`, and `ignore`.",
                param,
                ctx,
            )


class PyVersionParamType(click.ParamType):
    """ A parameter type for the --py-version CLI option """

    name = "py_version"

    def convert(self, value: str, param: Any, ctx: Any) -> PyVersion:

        # Reference: "Currently major must equal to 3." from https://docs.python.org/3/library/ast.html#ast.parse
        valid_majors = [3]
        # Reference: "The lowest supported version is (3, 4); the highest is sys.version_info[0:2]." from https://docs.python.org/3/library/ast.html#ast.parse
        valid_minors = range(4, sys.version_info[1] + 1)
        valid_py_versions = [(x, y) for x in valid_majors for y in valid_minors]

        try:
            m = re.fullmatch(r"(?P<major>\d+)\.(?P<minor>\d+)", value)
            version = int(m.group("major")), int(m.group("minor"))
            if version not in valid_py_versions:
                raise ValueError
            return version

        except (AttributeError, ValueError):
            stringfy_valid_py_versions = ", ".join(
                f"{x}.{y}" for x, y in valid_py_versions
            )
            self.fail(
                "--py argument has invalid value. "
                f"Possible values are {stringfy_valid_py_versions}.",
                param,
                ctx,
            )


# TODO provide a programmatical interface. Check if click library provides such a functionality, to turn a CLI interface to programmatical interface.


# TODO add -V as short option of --version
@click.command(
    name="absort",
    help="A command line utility to sort Python source code by abstraction levels",
    no_args_is_help=True,  # type: ignore
    context_settings=dict(help_option_names=["-h", "--help", "/?"]),
    epilog="While the tool is in the experimental stage, all files are backuped to a local cache before processing. "
    "If something goes wrong or regret hits you, it's always possible to safely recover the original files. "
    'The location of the backup cache is "~/.absort_cache".',
)
@click.argument(
    "filepaths",
    nargs=-1,
    metavar="<files or directories to search for Python files>",
    # We don't test writable, because it's possible user just want to see diff, instead of
    # in-place updating the file.
    #
    # FIXME what's the semantic to specify allow_dash=True for click.Path when value is a directory?
    # FIXME what's the semantic to specify readable=True for click.Path when value is a directory?
    # TODO use callback to transform filepaths from tuple[str] to tuple[Path]
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, allow_dash=True
    ),
)
@click.option(
    "-c", "--check", is_flag=True, help="Check if the file is already well-formatted."
)
@click.option(
    "-d",
    "--diff",
    "display_diff",
    is_flag=True,
    help="Specify whether to display the diff view between the original source code and the new source code.",
)
@click.option(
    "-i",
    "--in-place",
    is_flag=True,
    help="Specify whether to modify the file in-place. This is a dangerous option. Use to "
    "your own risk. A confirmation prompt shows up to give you second chance to think over.",
)
@click.option(
    "--no-fix-main-to-bottom",
    is_flag=True,
    help="Specify that the main function doesn't need to be fixed to the bottom-most. "
    "The default behavior of the program is to fix the main function to the bottom-most, "
    "unless the `--no-fix-main-to-bottom` option is set.",
)
@click.option(
    "-r",
    "--reverse",
    is_flag=True,
    help="Reverse the sort order. The default order is that the higher the abstraction "
    "level the topper it locates.",
)
@click.option(
    "--no-aggressive",
    is_flag=True,
    help="Disable some aggressive transformations to the source code which are mostly for cosmetic purpose. "
    "Setting this option retains more original code layout, hence reducing diff size, if that is desirable.",
)
@click.option(
    "-e",
    "--encoding",
    metavar="ENCODING",
    default="utf-8",
    show_default=True,
    help="The encoding scheme used to read and write Python files.",
)
@click.option(
    "--comment-strategy",
    default="attr-follow-decl",
    show_default=True,
    type=CommentStrategyParamType(),
    help="Specify how to treat comments. Possible values are `push-top`, "
    "`attr-follow-decl`, and `ignore` (not recommended). The default value is "
    "`attr-follow-decl`. `push-top` specifies that all comments are pushed to top. "
    "`attr-follow-decl` specifies that comments are treated as attribute of the following "
    "declaration. `ignore` specifies that comments are ignored and removed.",
)
@click.option(
    "--py",
    "py_version",
    default="3.9",
    show_default=True,
    type=PyVersionParamType(),
    help="Specify the version of Python abstract grammar being used in parsing input files.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress all output except the error channel. To also suppress error channel please use `2>/dev/null`.",
)
@click.option("-v", "--verbose", is_flag=True, help="Increase verboseness.")
@click.option(
    "--color-off",
    is_flag=True,
    help="Turn off color output. For compatibility with environment without color code support.",
)
@click.option(
    "-y",
    "--yes",
    "bypass_prompt",
    is_flag=True,
    help="Bypass all confirmation prompts. Dangerous option. Not recommended.",
)
@click.option("--dfs", is_flag=True, help="Sort in depth-first order.")
@click.option("--bfs", is_flag=True, help="Sort in breadth-first order.")
@click.option(
    "--separate-class-and-function",
    is_flag=True,
    help="Specify that class definitions and function definitions should be separated into respective sections.",
)
@click.version_option(__version__)
@click.pass_context
# TODO add command line option to ignore files specified by .gitignore
# TODO add command line option to customize cache location
@profile  # type: ignore
def main(
    ctx: click.Context,
    filepaths: tuple[str, ...],
    check: bool,
    display_diff: bool,
    in_place: bool,
    no_fix_main_to_bottom: bool,
    reverse: bool,
    no_aggressive: bool,
    encoding: str,
    comment_strategy: CommentStrategy,
    py_version: PyVersion,
    quiet: bool,
    verbose: bool,
    color_off: bool,
    bypass_prompt: bool,
    dfs: bool,
    bfs: bool,
    separate_class_and_function: bool,
) -> None:
    """ the CLI entry """

    options = SimpleNamespace(**ctx.params)
    validate_args(options)

    # First confirmation prompt
    if bypass_prompt:
        ans = click.confirm(
            "Are you sure you want to bypass all confirmation prompts? "
            "(Dangerous, not recommended)"
        )
        if not ans:
            bypass_prompt = False

    # Second confirmation prompt
    if bypass_prompt:
        ans = click.confirm(
            "Are you REALLY REALLY REALLY sure you want to bypass all confirmation prompts? "
            "(Dangerous, not recommended)"
        )
        if not ans:
            bypass_prompt = False

    files = list(collect_python_files(map(Path, filepaths)))
    if not files:
        print("No file is found")
        return
    print(f"Found {len(files)} files")

    format_option = FormatOption(  # type: ignore
        no_aggressive=no_aggressive,
        reverse=reverse,
        no_fix_main_to_bottom=no_fix_main_to_bottom,
        separate_class_and_function=separate_class_and_function,
    )

    if display_diff:
        file_action = FileAction.DIFF
    elif in_place:
        file_action = FileAction.WRITE
    elif check:
        file_action = FileAction.CHECK
    else:
        file_action = FileAction.PRINT

    if dfs:
        sort_order = SortOrder.DEPTH_FIRST
    elif bfs:
        sort_order = SortOrder.BREADTH_FIRST
    else:
        sort_order = SortOrder.TOPOLOGICAL

    verboseness_context_manager = silent_context() if quiet else contextlib.nullcontext()

    # TODO test --color-off under different environments, eg. Linux, macOS, ...
    colorness_context_manager = no_color_context() if color_off else colorama_text()

    with verboseness_context_manager, colorness_context_manager:

        digest = absort_files(
            files,
            encoding,
            bypass_prompt,
            verbose,
            file_action,
            py_version,
            comment_strategy,
            format_option,
            sort_order,
        )

        display_summary(digest)


def validate_args(options: SimpleNamespace) -> None:
    """ Preliminary check of the validness of the CLI argument """

    # FIXME use click library's builtin mechanism to specify mutually exclusive options

    def mutually_exclusive(*args: str) -> None:
        if sum(bool(getattr(options, arg)) for arg in args) > 1:
            if len(args) == 2:
                raise ValueError(
                    f"Can't specify both `{args[0]}` and `{args[1]}` options"
                )
            else:
                fargs = [f"`{arg}`" for arg in args]
                opts = ", ".join(fargs[:-1]) + " and " + fargs[-1]
                raise ValueError(
                    f"Only one of the {opts} options can be specified at the same time"
                )

    mutually_exclusive("check", "display_diff", "in_place")
    mutually_exclusive("quiet", "verbose")
    mutually_exclusive("dfs", "bfs")


@run_in_event_loop
async def collect_python_files(filepaths: Iterable[Path]) -> AsyncIterator[Path]:
    """ Yield python files searched from the given paths """

    for filepath in filepaths:
        if not await filepath.exists():
            print(f'File "{filepath}" doesn\'t exist. Skipped.', file=sys.stderr)
        elif await filepath.is_file():

            # We don't test file suffix, because it's possible user explicitly enters an
            # input file that contains Python code but doesn't have `.py` extension.
            # If it doesn't contain Python code, a SyntaxError will be raised from other
            # part of the code and handled by exception handling routines anyway.
            yield filepath

        elif await filepath.is_dir():

            async for p in filepath.rglob("*.py"):
                yield p

        else:
            raise NotImplementedError


def absort_files(
    files: list[Path],
    encoding: str = "utf-8",
    bypass_prompt: bool = False,
    verbose: bool = False,
    file_action: FileAction = FileAction.PRINT,
    py_version: PyVersion = (3, 9),
    comment_strategy: CommentStrategy = CommentStrategy.ATTR_FOLLOW_DECL,
    format_option: FormatOption = FormatOption(),
    sort_order: SortOrder = SortOrder.TOPOLOGICAL,
) -> Digest:
    """ Sort a list of files """

    # TODO use multi-processing to boost speed of handling a bunch of files (CPU-bound parts)

    async def entry() -> Digest:
        tasks = (
            absort_file(
                file,
                encoding,
                bypass_prompt,
                verbose,
                file_action,
                py_version,
                comment_strategy,
                format_option,
                sort_order,
            )
            for file in files
        )
        digests = await asyncio.gather(*tasks)
        return sum(digests, Digest())

    return asyncio.run(entry())


@profile  # type: ignore
async def absort_file(
    file: Path,
    encoding: str = "utf-8",
    bypass_prompt: bool = False,
    verbose: bool = False,
    file_action: FileAction = FileAction.PRINT,
    py_version: PyVersion = (3, 9),
    comment_strategy: CommentStrategy = CommentStrategy.ATTR_FOLLOW_DECL,
    format_option: FormatOption = FormatOption(),
    sort_order: SortOrder = SortOrder.TOPOLOGICAL,
) -> Digest:
    """ Sort the source in the given file """

    async def read_source(file: Path) -> str:
        """ Read source from the file, including exception handling """

        try:
            return await file.read_text(encoding)
        except UnicodeDecodeError:
            print(f"{file} is not decodable by {encoding}", file=sys.stderr)
            print(f"Try to automatically detect file encoding......", file=sys.stderr)
            binary = await file.read_bytes()
            detected_encoding = cchardet.detect(binary)["encoding"]

            try:
                return await file.read_text(detected_encoding)
            except UnicodeDecodeError:

                print(f"{file} has unknown encoding.", file=sys.stderr)
                raise ABSortFail

    def absort_source(old_source: str) -> str:
        """ Sort the source in string, including exception handling """

        try:
            return absort_str(
                old_source, py_version, comment_strategy, format_option, sort_order
            )
        except SyntaxError as exc:
            # if re.fullmatch(r"Missing parentheses in call to 'print'. Did you mean print(.*)\?", exc.msg):
            #     pass
            print(f"{file} has erroneous syntax: {exc.msg}", file=sys.stderr)
            raise ABSortFail

        except NameRedefinition:
            print(
                f"{file} contains duplicate name redefinitions. Not supported yet.",
                file=sys.stderr,
            )
            raise ABSortFail

    async def write_source(file: Path, new_source: str) -> None:
        """ Write the new source to the file, prompt for confirmation and make backup """

        if not bypass_prompt:
            ans = click.confirm(
                f"Are you sure you want to in-place update the file {file}?", err=True
            )
            if not ans:
                digest.unmodified += 1
                return

        await backup_to_cache(file)

        await file.write_text(new_source, encoding)
        digest.modified += 1
        if verbose:
            print(bright_green(f"Processed {file}"))

    async def process_new_source(new_source: str) -> None:
        """ Process the new source as specified by the CLI arguments """

        # TODO add more styled output (e.g. colorized)

        if file_action is FileAction.DIFF:

            digest.unmodified += 1
            display_diff_with_filename(old_source, new_source, str(file))

        elif file_action is FileAction.WRITE:

            if old_source == new_source:
                digest.unmodified += 1
                return
            await write_source(file, new_source)

        elif file_action is FileAction.CHECK:

            digest.unmodified += 1
            if old_source != new_source:
                print(f"{file} needs reformat")

        elif file_action is FileAction.PRINT:
            digest.unmodified += 1
            divider = bright_yellow("-" * 79)
            print(divider)
            print(file)
            print(divider)
            print(new_source)
            print(divider)
            print("\n", end="")

        else:
            raise ValueError("the file_action argument receives invalid value")

    try:
        digest = Digest()
        old_source = await read_source(file)
        new_source = absort_source(old_source)
        await process_new_source(new_source)
        return digest
    except ABSortFail:
        return Digest(failed=1)  # type: ignore


@profile  # type: ignore
def absort_str(
    old_source: str,
    py_version: PyVersion = (3, 9),
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
    new_source_lines = strict_splitlines(old_source)

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

    return new_source


def find_continguous_decls(
    stmts: list[ast.stmt],
) -> Iterator[tuple[int, int, list[DeclarationType]]]:
    """ Yield blocks of continguous declarations """

    # WARNING: lineno and end_lineno are 1-indexed

    head_sentinel = ast.stmt()
    head_sentinel.lineno = head_sentinel.end_lineno = 0
    stmts.insert(0, head_sentinel)

    tail_sentinel = ast.stmt()
    tail_sentinel.lineno = tail_sentinel.end_lineno = stmts[-1].end_lineno + 1
    stmts.append(tail_sentinel)

    buffer: list[DeclarationType] = []
    last_nondecl_stmt = head_sentinel
    lineno: int = 0
    end_lineno: int = 0

    for stmt in stmts[1:]:
        if isinstance(stmt, Declaration):
            lineno = last_nondecl_stmt.end_lineno + 1
            assert stmt.end_lineno is not None
            end_lineno = stmt.end_lineno
            buffer.append(stmt)
        else:
            if buffer:
                yield lineno, end_lineno, buffer
                buffer.clear()
            last_nondecl_stmt = stmt


@profile  # type: ignore
def absort_decls(
    decls: Sequence[DeclarationType],
    py_version: PyVersion,
    format_option: FormatOption,
    sort_order: SortOrder,
) -> Iterator[DeclarationType]:
    """ Sort a continguous block of declarations """

    def same_abstract_level_sorter(names: Iterable[str]) -> Iterable[str]:
        """ Specify how to sort declarations within the same abstract level """

        # Currently sort by retaining their original relative order, to reduce diff size.
        #
        # Possible alternatives: sort by lexicographical order of the names, sort by body
        # size, sort by name length, etc.
        #
        # TODO More advanced option is to utilize power of machine learning to put two
        # visually/semantically similar function/class definitions near each other.
        #
        # Code similarity can be implemented in:
        # 1. easy and naive way: source code string similarity. eg. shortest edit distance algorithm.
        # 2. sophisticated way: syntax tree similarity. E.g. the classic Zhange-Shaha algorithm.

        if format_option.no_aggressive:
            decl_name_inverse_index = {name: idx for idx, name in enumerate(decl_names)}
            return sorted(names, key=lambda name: decl_name_inverse_index[name])

        else:
            # Sort by putting two visually similar definitions together

            name_lookup_table = {decl.name: decl for decl in decls}
            same_level_decls = [name_lookup_table[name] for name in names]
            sorted_decls = sort_decls_by_syntax_tree_similarity(same_level_decls)
            return (decl.name for decl in sorted_decls)

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

    if sort_order is SortOrder.TOPOLOGICAL:
        sccs = ireverse(graph.strongly_connected_components())
        sorted_names = list(chain(*(same_abstract_level_sorter(scc) for scc in sccs)))

    elif sort_order in (SortOrder.DEPTH_FIRST, SortOrder.BREADTH_FIRST):
        if sort_order is SortOrder.DEPTH_FIRST:
            traverse_method = graph.dfs
        elif sort_order is SortOrder.BREADTH_FIRST:
            traverse_method = graph.bfs
        else:
            raise Unreachable

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
        raise Unreachable

    if format_option.reverse:
        sorted_names.reverse()

    if not format_option.no_fix_main_to_bottom and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    # There is always one, and only one, decl that matches the name, we use
    # short-circuit to optimize.
    for name in sorted_names:
        name_matcher = lambda decl: decl.name == name
        yield first_true(decls, pred=name_matcher)  # type: ignore


def sort_decls_by_syntax_tree_similarity(
    decls: list[DeclarationType],
) -> Iterator[DeclarationType]:
    if len(decls) == 1:
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

            # A heuristic. If only whitespaces are present, compress to two blank lines.
            # Because it's visually bad to have zero or too many blank lines between
            # two declarations. So we explicitly add it. Two blank lines between
            # declarations is PEP8 style (https://pep8.org/#blank-lines)
            source_lines += "\n\n".splitlines()

        elif related_source_lines[0].strip():

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
        raise Unreachable

    source_lines += ast_get_source_lines(source, node)

    return source_lines


async def backup_to_cache(file: Path) -> None:
    """ Make a backup of the file, put in the cache """

    def generate_timestamp() -> str:
        now = str(datetime.now())
        timestamp = ""
        for char in now:
            if char.isdigit():
                timestamp += char
        return timestamp[:14]

    timestamp = generate_timestamp()
    backup_file = CACHE_DIR / (file.name + "." + timestamp + ".backup")

    await CACHE_DIR.mkdir(parents=True, exist_ok=True)
    await file.copy2(backup_file)

    if await CACHE_DIR.dirsize() > CACHE_MAX_SIZE:
        await shrink_cache()


async def shrink_cache() -> None:
    """ Shrink the size of cache to under threshold """

    shrink_target_size = CACHE_MAX_SIZE - await CACHE_DIR.dirsize()

    backup_filename_pattern = r".*\.(?P<timestamp>\d{14})\.backup"

    files: list[tuple[str, Path]] = []
    async for f in CACHE_DIR.iterdir():
        if m := re.fullmatch(backup_filename_pattern, f.name):
            timestamp = m.group("timestamp")
            files.append((timestamp, f))

    sorted_files = sorted(files, key=itemgetter(0))

    shrinked_size = 0
    for _, f in sorted_files:
        stat = await f.stat()
        shrinked_size += stat.st_size
        await f.unlink()
        if shrinked_size >= shrink_target_size:
            break


def display_diff_with_filename(
    old_src: str, new_src: str, filename: str = None
) -> None:
    """ Display diff view between old source and new source """

    old_src_lines = old_src.splitlines(keepends=True)
    new_src_lines = new_src.splitlines(keepends=True)

    fromfile = "old/" + filename if filename else ""
    tofile = "new/" + filename if filename else ""

    diff_view_lines = colored_unified_diff(
        old_src_lines, new_src_lines, fromfile, tofile
    )

    print("".join(diff_view_lines), end="")
    print("\n", end="")


def display_summary(digest: Digest) -> None:
    """ Display the succint summary of the sorting process """

    summary = []
    for field in attr.fields(Digest):
        description = field.name
        file_num = digest[description]
        if not file_num:
            continue
        plurality_suffix = "s" if file_num > 1 else ""
        summary.append(f"{file_num} file{plurality_suffix} {description}")
    print(", ".join(summary) + ".")


if __name__ == "__main__":
    main()
