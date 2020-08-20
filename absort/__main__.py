#!/usr/bin/env python3

import ast
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Set, Tuple

import click
import colorama
from more_itertools import first_true

from .ast_utils import (
    ast_get_decorator_list_source_lines,
    ast_get_leading_comment_and_decorator_list_source_lines,
    ast_get_leading_comment_source_lines,
    ast_get_source_lines,
)
from .extra_typing import Declaration, DeclarationType
from .graph import CircularDependencyError, Graph
from .utils import colored_unified_diff
from .visitors import GetUndefinedVariableVisitor


# Note: the name `profile` will be injected by line-profiler at run-time
try:
    profile  # type: ignore
except NameError:
    profile = lambda x: x


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


def get_dependency_of_decl(decl: DeclarationType) -> Set[str]:
    temp_module = ast.Module(body=[decl])
    visitor = GetUndefinedVariableVisitor()
    return visitor.visit(temp_module)


@profile  # type: ignore
def absort_decls(decls: List[DeclarationType]) -> Iterator[DeclarationType]:
    def same_rank_sorter(names: List[str]) -> List[str]:
        # Currently sort by retaining their original relative order, to reduce diff size.
        #
        # Possible alternatives: sort by lexigraphical order of the names, sort by body
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

    graph = Graph()
    for decl in decls:
        deps = get_dependency_of_decl(decl)
        for dep in deps:
            if dep in decl_names:
                graph.add_edge(decl.name, dep)
    sorted_names = list(graph.hierarchy_level_sort(same_rank_sorter=same_rank_sorter))

    cli_params = click.get_current_context().params

    if cli_params["reverse"]:
        sorted_names.reverse()

    if not cli_params["no_fix_main_to_bottom"] and "main" in sorted_names:
        sorted_names.remove("main")
        sorted_names.append("main")

    # There is always one, and only one, decl that matches the name, we use
    # short-circuit to optimize.
    for name in sorted_names:
        name_matcher = lambda decl: decl.name == name
        yield first_true(decls, pred=name_matcher)  # type: ignore


@profile  # type: ignore
def transform(old_source: str) -> str:
    @profile  # type: ignore
    def get_related_source_lines(source: str, node: ast.AST) -> str:
        leading_comment_source_lines = ast_get_leading_comment_source_lines(
            source, node
        )
        decorator_list_source_lines = ast_get_decorator_list_source_lines(source, node)

        source_lines = ""

        if comment_strategy is CommentStrategy.push_top:
            nonlocal comments  # type: ignore
            comments += leading_comment_source_lines + "\n"
            source_lines += decorator_list_source_lines + "\n"
        elif comment_strategy is CommentStrategy.attr_follow_decl:
            # fmt: off
            source_lines += ast_get_leading_comment_and_decorator_list_source_lines(
                source, node
            ) + "\n"
            # fmt: on
        elif comment_strategy is CommentStrategy.ignore:
            source_lines += decorator_list_source_lines + "\n"
        else:
            raise RuntimeError("Unreachable")

        source_lines += ast_get_source_lines(source, node) + "\n"

        return source_lines

    @profile  # type: ignore
    def transform_stmts(old_stmts: List[ast.stmt]) -> Iterator[ast.stmt]:
        buffer: List[DeclarationType] = []
        for stmt in old_stmts:
            if isinstance(stmt, Declaration):
                buffer.append(stmt)
            else:
                yield from absort_decls(buffer)
                buffer.clear()
                yield stmt
        yield from absort_decls(buffer)

    def preliminary_sanity_check(top_level_stmts: List[ast.stmt]) -> None:
        # TODO add more sanity checks

        decls = [stmt for stmt in top_level_stmts if isinstance(stmt, Declaration)]
        decl_names = [decl.name for decl in decls]

        if len(set(decl_names)) < len(decl_names):
            raise NameRedefinition("Name redefinition exists. Not supported yet.")

    module_tree = ast.parse(old_source)

    top_level_stmts = module_tree.body

    preliminary_sanity_check(top_level_stmts)

    new_stmts = transform_stmts(top_level_stmts)

    cli_params = click.get_current_context().params
    comment_strategy: CommentStrategy = cli_params["comment_strategy"]

    new_source = ""
    comments = ""
    for stmt in new_stmts:
        source_lines = get_related_source_lines(old_source, stmt)
        new_source += source_lines + "\n"

    if comment_strategy is CommentStrategy.push_top:
        new_source = comments + new_source

    return new_source


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
        if filepath.is_file():
            # We don't test file suffix, because it's possible user explicitly enters an
            # input file that contains Python code but doesn't have `.py` extension.
            # If it doesn't contain Python code, a SyntaxError will be raised from other
            # part of the code and handled by exception handling routines anyway.
            yield filepath
        elif filepath.is_dir():
            yield from filepath.rglob("*.py")
        else:
            raise NotImplementedError


@click.command()
@click.argument(
    "filepaths",
    nargs=-1,
    # We don't test writable, because it's possible user just want to see diff, instead of
    # in-place updating the file.
    #
    # FIXME what's the semantic to specify allow_dash=True for click.Path when value is a directory?
    # FIXME what's the semantic to specify readable=True for click.Path when value is a directory?
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, allow_dash=True
    ),
)
@click.option("-d", "--diff", "display_diff", is_flag=True)
@click.option("-i", "--in-place", is_flag=True)
@click.option("--no-fix-main-to-bottom", is_flag=True)
@click.option("-r", "--reverse", is_flag=True)
@click.option("-e", "--encoding", default="utf-8")
@click.option(
    "-c",
    "--comment-strategy",
    default="attr-follow-decl",
    type=CommentStrategyParamType(),
    help="Specify how to treat comments. Possible values are `push-top`, "
    "`attr-follow-decl`, and `ignore` (not recommended). The default value is "
    "`attr-follow-decl`.",
)
@click.option("-q", "--quiet", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
# TODO add multi thread support, to accelerate
# TODO add help message to every parameters.
# TODO add command line option --yes to bypass all confirmation prompts
# TODO add description as argument to click.command()
@profile  # type: ignore
def main(
    filepaths: Tuple[str],
    display_diff: bool,
    in_place: bool,
    no_fix_main_to_bottom: bool,
    reverse: bool,
    encoding: str,
    comment_strategy: CommentStrategy,
    quiet: bool,
    verbose: bool,
) -> None:

    if display_diff and in_place:
        raise ValueError("Can't specify both `--diff` and `--in-place` options")

    if quiet and verbose:
        raise ValueError("Can't specify both `--quiet` and `--verbose` options")

    if quiet:
        sys.stdout = open(os.devnull, "a")
        sys.stderr = open(os.devnull, "a")

    colorama.init()

    files = collect_python_files(map(Path, filepaths))

    for file in files:
        try:
            old_source = file.read_text(encoding)
        except UnicodeDecodeError:
            print(f"{file} has unknown encoding.")
            continue

        try:
            new_source = transform(old_source)
        except SyntaxError as exc:
            # if re.fullmatch(r"Missing parentheses in call to 'print'. Did you mean print(.*)\?", exc.msg):
            #     pass
            print(f"{file} has erroneous syntax: {exc.msg}")
            continue
        except NameRedefinition:
            print(f"{file} contains duplicate name redefinitions. Not supported yet.")
            continue
        except CircularDependencyError:
            print(f"{file} contains circular dependency. Not supported yet.")
            continue

        # TODO add more styled output (e.g. colorized)

        if display_diff:
            # WARNING: Path.name is different from Path.__str__()
            # Path.name is "A string representing the final path component, excluding the drive and root, if any"
            # Path.__str__ is "The string representation of a path is the raw filesystem path itself (in native form, e.g. with backslashes under Windows), which you can pass to any function taking a file path as a string"
            display_diff_with_filename(old_source, new_source, str(file))
        elif in_place:
            click.confirm(
                f"Are you sure you want to in-place update the file {file}?", abort=True
            )
            file.write_text(new_source, encoding)
        else:
            print("---------------------------------------")
            print(file)
            print("***************************************")
            print(new_source)
            print("***************************************")
            print("\n", end="")

        if verbose:
            print(f"Processed {file}")


if __name__ == "__main__":
    main()
