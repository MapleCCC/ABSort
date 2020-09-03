#!/usr/bin/env python3

import ast
import asyncio
import contextlib
import os
import re
import shutil
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from operator import itemgetter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Iterator, List, Set, Tuple

import click
from colorama import colorama_text

from .__version__ import __version__
from .ast_utils import (
    ast_get_decorator_list_source_lines,
    ast_get_leading_comment_and_decorator_list_source_lines,
    ast_get_leading_comment_source_lines,
    ast_get_source_lines,
)
from .extra_typing import Declaration, DeclarationType
from .graph import Graph
from .utils import (
    SingleThreadPoolExecutor,
    bright_yellow,
    colored_unified_diff,
    compose,
    detect_encoding,
    dirsize,
    first_true,
    silent_context,
    whitespace_lines,
    xreverse,
)
from .visitors import GetUndefinedVariableVisitor


CACHE_DIR = Path.home() / ".absort_cache"
CACHE_MAX_SIZE = 400000  # unit is byte

SINGLE_THREAD_APROACH_MAX_DECLNUM = 3

# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


# A global variable to store CLI arguments.
args = SimpleNamespace()


# A singleton object to signal failure
Fail = object()


# Alternative name: DuplicateNames
class NameRedefinition(Exception):
    pass


class CommentStrategy(Enum):
    push_top = "push-top"
    attr_follow_decl = "attr-follow-decl"
    ignore = "ignore"


class CommentStrategyParamType(click.ParamType):
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
    name = "py_version"

    def convert(self, value: str, param: Any, ctx: Any) -> Tuple[int, int]:
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


def get_dependency_of_decl(decl: DeclarationType) -> Set[str]:
    call_stmt = ast.Expr(
        value=ast.Call(
            func=ast.Name(id=decl.name, ctx=ast.Load()), args=[], keywords=[]
        )
    )
    temp_module = ast.Module(body=[decl, call_stmt], type_ignores=[])

    # temp_module = ast.Module()
    # temp_module.body = []
    # temp_module.body.append(decl)
    # name = ast.Name(id=decl.name, ctx=ast.Load())
    # call_stmt = ast.Expr(value=ast.Call(func=name, args=[], keywords=[]))
    # temp_module.body.append(call_stmt)
    # temp_module.type_ignores = []

    visitor = GetUndefinedVariableVisitor(py_version=args.py_version)
    return visitor.visit(temp_module)


def generate_dependency_graph(decls: List[DeclarationType]) -> Graph:
    decl_names = [decl.name for decl in decls]

    graph = Graph()

    if len(decls) <= SINGLE_THREAD_APROACH_MAX_DECLNUM:
        thread_pool_executor = SingleThreadPoolExecutor
    else:
        thread_pool_executor = ThreadPoolExecutor

    with thread_pool_executor() as executor:
        depses = executor.map(get_dependency_of_decl, decls)
        for decl, deps in zip(decls, depses):

            for dep in deps:
                if dep in decl_names:
                    graph.add_edge(decl.name, dep)

            # Below line is necessary for adding node with zero out-degree to the graph.
            graph.add_node(decl.name)

    return graph


@profile  # type: ignore
def absort_decls(decls: List[DeclarationType]) -> Iterator[DeclarationType]:
    def same_abstract_level_sorter(names: List[str]) -> List[str]:
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
        # 2. sophisticated way: syntax tree similarity.

        decl_name_inverse_index = {name: idx for idx, name in enumerate(decl_names)}
        return sorted(names, key=lambda name: decl_name_inverse_index[name])

    decl_names = [decl.name for decl in decls]
    if len(set(decl_names)) < len(decl_names):
        raise NameRedefinition("Name redefinition exists. Not supported yet.")

    graph = generate_dependency_graph(decls)

    sorted_names = xreverse(
        graph.relaxed_topological_sort(
            reverse=True, same_rank_sorter=compose(xreverse, same_abstract_level_sorter)
        )
    )

    if args.reverse:
        sorted_names.reverse()

    if not args.no_fix_main_to_bottom and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    # There is always one, and only one, decl that matches the name, we use
    # short-circuit to optimize.
    for name in sorted_names:
        name_matcher = lambda decl: decl.name == name
        yield first_true(decls, pred=name_matcher)


@profile  # type: ignore
def get_related_source_lines_of_decl(source: str, node: ast.AST) -> List[str]:
    source_lines = []

    if args.comment_strategy is CommentStrategy.attr_follow_decl:
        source_lines += ast_get_leading_comment_and_decorator_list_source_lines(
            source, node
        )
    elif args.comment_strategy in (CommentStrategy.push_top, CommentStrategy.ignore):
        source_lines += ast_get_decorator_list_source_lines(source, node)
    else:
        raise RuntimeError("Unreachable")

    source_lines += ast_get_source_lines(source, node)

    return source_lines


def find_continguous_decls(
    stmts: List[ast.stmt],
) -> Iterator[Tuple[int, int, List[DeclarationType]]]:
    # WARNING: lineno and end_lineno are 1-indexed

    head_sentinel = ast.stmt()
    head_sentinel.lineno = head_sentinel.end_lineno = 0
    stmts.insert(0, head_sentinel)

    tail_sentinel = ast.stmt()
    tail_sentinel.lineno = tail_sentinel.end_lineno = stmts[-1].end_lineno + 1
    stmts.append(tail_sentinel)

    buffer: List[DeclarationType] = []
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
def transform(old_source: str) -> str:
    def preliminary_sanity_check(top_level_stmts: List[ast.stmt]) -> None:
        # TODO add more sanity checks

        decls = [stmt for stmt in top_level_stmts if isinstance(stmt, Declaration)]
        decl_names = [decl.name for decl in decls]

        if len(set(decl_names)) < len(decl_names):
            raise NameRedefinition("Name redefinition exists. Not supported yet.")

    module_tree = ast.parse(old_source, feature_version=args.py_version)

    top_level_stmts = module_tree.body

    preliminary_sanity_check(top_level_stmts)

    blocks = find_continguous_decls(top_level_stmts)

    new_source_lines = old_source.splitlines()

    for lineno, end_lineno, decls in blocks:
        sorted_decls = list(absort_decls(decls))
        source_lines = get_related_source_lines_of_block(old_source, sorted_decls)
        new_source_lines[lineno - 1 : end_lineno] = source_lines

    new_source = "\n".join(new_source_lines) + "\n"

    # This line is a heuristic. It's visually bad to have blank lines at the
    # start of the document. So we explicitly remove them.
    new_source = new_source.lstrip()

    return new_source


def get_related_source_lines_of_block(
    source: str, decls: List[DeclarationType]
) -> List[str]:
    source_lines = []

    for decl in decls:

        related_source_lines = get_related_source_lines_of_decl(source, decl)

        if args.no_aggressive:
            source_lines += related_source_lines
        elif whitespace_lines(related_source_lines):

            # A heuristic. If only whitespaces are present, compress to two blank lines.
            # Because it's visually bad to have zero or too many blank lines between
            # two declarations. So we explicitly add it. Two blank lines between
            # declarations are black style (https://github.com/psf/black.)
            source_lines += "\n\n".splitlines()

        elif related_source_lines[0].strip():

            # A heuristic. It's visually bad to have no blank lines
            # between two declarations. So we explicitly add it. Two blank lines between
            # declarations are black style (https://github.com/psf/black.)
            source_lines += "\n\n".splitlines() + related_source_lines

        else:
            source_lines += related_source_lines

    if args.comment_strategy is CommentStrategy.push_top:
        total_comment_lines = []
        for decl in decls:
            comment_lines = ast_get_leading_comment_source_lines(source, decl)

            # A heuristic to return empty result if only whitespaces are present
            if not whitespace_lines(comment_lines):
                total_comment_lines += comment_lines

        source_lines = total_comment_lines + source_lines

    return source_lines


def display_diff_with_filename(
    old_src: str, new_src: str, filename: str = None
) -> None:
    old_src_lines = old_src.splitlines(keepends=True)
    new_src_lines = new_src.splitlines(keepends=True)

    fromfile = "old/" + filename if filename else ""
    tofile = "new/" + filename if filename else ""

    diff_view_lines = colored_unified_diff(
        old_src_lines, new_src_lines, fromfile, tofile
    )

    print("".join(diff_view_lines), end="")
    print("\n", end="")


def collect_python_files(filepaths: Iterable[Path]) -> Iterator[Path]:
    for filepath in filepaths:
        if not filepath.exists():
            print(f'File "{filepath}" doesn\'t exist. Skipped.')
        elif filepath.is_file():

            # We don't test file suffix, because it's possible user explicitly enters an
            # input file that contains Python code but doesn't have `.py` extension.
            # If it doesn't contain Python code, a SyntaxError will be raised from other
            # part of the code and handled by exception handling routines anyway.
            yield filepath

        elif filepath.is_dir():
            yield from filepath.rglob("*.py")
        else:
            raise NotImplementedError


def shrink_cache() -> None:
    shrink_target_size = CACHE_MAX_SIZE - dirsize(CACHE_DIR)

    backup_filename_pattern = r".*\.(?P<timestamp>\d{14})\.backup"

    files = []
    for f in CACHE_DIR.iterdir():
        if m := re.fullmatch(backup_filename_pattern, f.name):
            timestamp = m.group("timestamp")
            files.append((timestamp, f))

    sorted_files = sorted(files, key=itemgetter(0))

    shrinked_size = 0
    for _, f in sorted_files:
        shrinked_size += f.stat().st_size
        f.unlink()
        if shrinked_size >= shrink_target_size:
            break


def backup_to_cache(file: Path) -> None:
    def generate_timestamp() -> str:
        now = str(datetime.now())
        timestamp = ""
        for char in now:
            if char.isdigit():
                timestamp += char
        return timestamp[:14]

    timestamp = generate_timestamp()
    backup_file = CACHE_DIR / (file.name + "." + timestamp + ".backup")

    if not CACHE_DIR.is_dir():
        os.makedirs(CACHE_DIR)
    shutil.copy2(file, backup_file)

    if dirsize(CACHE_DIR) > CACHE_MAX_SIZE:
        shrink_cache()


# FIXME race condition on printing to console
# FIXME race condition on digest variable
def absort_files(files: List[Path], digest: Counter) -> None:
    async def read_source(file: Path) -> str:
        try:
            return file.read_text(args.encoding)
        except UnicodeDecodeError:

            print(f"{file} is not decodable by {args.encoding}", file=sys.stderr)
            print(f"Try to automatically detect file encoding......", file=sys.stderr)
            detected_encoding = detect_encoding(str(file))

            try:
                return file.read_text(detected_encoding)
            except UnicodeDecodeError:

                print(f"{file} has unknown encoding.", file=sys.stderr)
                return Fail  # type: ignore

    async def transform_source(old_source: str) -> str:
        if old_source is Fail:
            return Fail  # type: ignore

        try:
            return transform(old_source)
        except SyntaxError as exc:

            # if re.fullmatch(r"Missing parentheses in call to 'print'. Did you mean print(.*)\?", exc.msg):
            #     pass
            print(f"{file} has erroneous syntax: {exc.msg}", file=sys.stderr)
            return Fail  # type: ignore

        except NameRedefinition:

            print(
                f"{file} contains duplicate name redefinitions. Not supported yet.",
                file=sys.stderr,
            )
            return Fail  # type: ignore

    async def write_source(file: Path, new_source: str) -> None:
        ans = click.confirm(
            f"Are you sure you want to in-place update the file {file}?", err=True
        )
        if not ans:
            digest["unmodified"] += 1
            return

        backup_to_cache(file)

        file.write_text(new_source, args.encoding)
        digest["modified"] += 1
        if args.verbose:
            print(f"Processed {file}")

    async def process_new_source(new_source: str, old_source: str) -> None:
        if new_source is Fail:
            digest["failed"] += 1
            return

        # TODO add more styled output (e.g. colorized)

        if args.display_diff:

            digest["unmodified"] += 1
            display_diff_with_filename(old_source, new_source, str(file))

        elif args.in_place:

            if old_source == new_source:
                digest["unmodified"] += 1
                return
            await write_source(file, new_source)

        else:
            digest["unmodified"] += 1
            divider = bright_yellow("-" * 79)
            print(divider)
            print(file)
            print(divider)
            print(new_source)
            print(divider)
            print("\n", end="")

    async def absort_file(file: Path) -> None:
        old_source = await read_source(file)
        new_source = await transform_source(old_source)
        await process_new_source(new_source, old_source)

    for file in files:
        asyncio.run(absort_file(file))


def display_summary(digest: Counter) -> None:
    summary = []
    if digest["modified"]:
        summary.append(f"{digest['modified']} files modified")
    if digest["unmodified"]:
        summary.append(f"{digest['unmodified']} files unmodified")
    if digest["failed"]:
        summary.append(f"{digest['failed']} files failed")
    print(", ".join(summary) + ".")


def check_args() -> None:
    # FIXME use click library's builtin mechanism to specify mutually exclusive options

    if args.display_diff and args.in_place:
        raise ValueError("Can't specify both `--diff` and `--in-place` options")

    if args.quiet and args.verbose:
        raise ValueError("Can't specify both `--quiet` and `--verbose` options")


# TODO provide a programmatical interface. Check if click library provides such a functionality, to turn a CLI interface to programmatical interface.

# TODO add -h option
# TODO add -V as short option of --version
@click.command(
    name="absort",
    help="A command line utility to sort Python source code by abstraction levels",
    no_args_is_help=True,  # type: ignore
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
    # TODO use callback to transform filepaths from Tuple[str] to Tuple[Path]
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, allow_dash=True
    ),
)
@click.option(
    "-d",
    "--diff",
    "display_diff",
    is_flag=True,
    help="Specify whether to display diff view between the original source code and the new source code.",
)
@click.option(
    "-i",
    "--in-place",
    is_flag=True,
    help="Specify whether to modify file in-place. This is a dangerous option. Use to "
    "your own risk. A confirmation prompt shows up to give you second chance to think over.",
)
@click.option(
    "--no-fix-main-to-bottom",
    is_flag=True,
    help="Specify that main function doesn't need to be fixed to the bottom-most. "
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
    "-c",
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
    default="3.8",
    show_default=True,
    type=PyVersionParamType(),
    help="Specify the version of Python abstract grammar being used in parsing input files.",
)
@click.option(
    "-q", "--quiet", is_flag=True, help="Suppress all output except the error channel."
)
@click.option("-v", "--verbose", is_flag=True, help="Increase verboseness.")
@click.version_option(__version__)
@click.pass_context
# TODO add command line option --yes to bypass all confirmation prompts
@profile  # type: ignore
def main(
    ctx: click.Context,
    filepaths: Tuple[str],
    display_diff: bool,
    in_place: bool,
    no_fix_main_to_bottom: bool,
    reverse: bool,
    no_aggressive: bool,
    encoding: str,
    comment_strategy: CommentStrategy,
    py_version: Tuple[int, int],
    quiet: bool,
    verbose: bool,
) -> None:

    # A global variable to store CLI arguments.
    global args
    for param_name, param_value in ctx.params.items():
        setattr(args, param_name, param_value)

    check_args()

    files = list(collect_python_files(map(Path, filepaths)))
    print(f"Found {len(files)} files")

    # TODO make digest a global variable so that we don't need to pass around
    digest: Counter = Counter(modified=0, unmodified=0, failed=0)

    verboseness_context_manager = silent_context() if quiet else contextlib.nullcontext()

    with verboseness_context_manager, colorama_text():

        absort_files(files, digest)

        display_summary(digest)


if __name__ == "__main__":
    main()
