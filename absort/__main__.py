#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import contextlib
import re
import shutil
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import datetime
from enum import Enum, IntEnum, auto
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import cchardet
import click
from colorama import colorama_text
from more_itertools import take
from recipes.misc import bright_green, bright_yellow, profile

from .__version__ import __version__
from .collections_extra import PriorityQueue
from .core import (
    CommentStrategy,
    FormatOption,
    NameRedefinition,
    SortOrder,
    absort_str,
)
from .typing_extra import PyVersion
from .utils import colorized_unified_diff, no_color_context, silent_context


__all__ = [
    "absort_str",
    "absort_file",
    "absort_files",
    "CommentStrategy",
    "FormatOption",
    "FileAction",
    "SortOrder",
    "NameRedefinition",
    "BypassPromptLevel",
]


#
# Enumerations
#


class FileAction(Enum):
    """An enumeration to specify different kinds of file actions"""

    CHECK = auto()
    DIFF = auto()
    PRINT = auto()
    WRITE = auto()


class FileResult(Enum):
    """An enumeration to specify different kinds of file results"""

    UNMODIFIED = "unmodified"
    MODIFIED = "modified"
    FAILED = "failed"


class BypassPromptLevel(IntEnum):
    """An enumeration to specify different bypass-prompt levels"""

    NO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    @property
    def MAX_LEVEL(cls: type[BypassPromptLevel]) -> int:
        return 3


#
# Constants
#

# Specify the location of the cache directory
CACHE_DIR = Path.home() / ".absort_cache"
# Specify the maximum size threshold for the cache directory (in bytes)
CACHE_MAX_SIZE = 400000  # unit is byte
CACHE_DIR_LOCK = asyncio.Lock()

#
# Type Annotations
#

#
# Global Variables
#

#
# Custom Exceptions
#


class ABSortFail(Exception):
    """An exception to signal that sorting fails"""


class MutuallyExclusiveOptions(Exception):
    """An exception to signal that two or more mutually exclusive CLI options are set"""


#
# Utility Classes
#


class CommentStrategyParamType(click.ParamType):
    """A parameter type for the --comment-strategy CLI option"""

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
    """A parameter type for the --py-version CLI option"""

    name = "py_version"

    def convert(self, value: str, param: Any, ctx: Any) -> PyVersion:

        # Reference: "Currently major must equal to 3." from https://docs.python.org/3/library/ast.html#ast.parse
        valid_majors = [3]
        # Reference: "The lowest supported version is (3, 4); the highest is sys.version_info[0:2]." from https://docs.python.org/3/library/ast.html#ast.parse
        valid_minors = range(4, sys.version_info[1] + 1)
        valid_py_versions = [(x, y) for x in valid_majors for y in valid_minors]

        try:
            m = re.fullmatch(r"(?P<major>\d+)\.(?P<minor>\d+)", value)
            if not m:
                raise ValueError
            version = int(m.group("major")), int(m.group("minor"))
            if version not in valid_py_versions:
                raise ValueError
            return version

        except ValueError:
            stringfy_valid_py_versions = ", ".join(
                f"{x}.{y}" for x, y in valid_py_versions
            )
            self.fail(
                "--py argument has invalid value. "
                f"Possible values are {stringfy_valid_py_versions}.",
                param,
                ctx,
            )


class BypassPromptParamType(click.ParamType):
    """A parameter type for the --yes CLI option"""

    name = "bypass_prompt"

    def convert(self, value: int, param: Any, ctx: Any) -> BypassPromptLevel:
        try:
            value = min(value, BypassPromptLevel.MAX_LEVEL)
            return BypassPromptLevel(value)

        except ValueError:
            self.fail("--yes flag has invalid count.", param, ctx)


# TODO provide a programmatical interface. Check if click library provides such a functionality, to turn a CLI interface to programmatical interface.


# TODO add -V as short option of --version
@click.command(
    name="absort",
    no_args_is_help=True,
    context_settings={"help_option_names":["-h", "--help", "/?"]},
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
    default="3.10",
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
    count=True,
    type=BypassPromptParamType(),
    help="Bypass confirmation prompts. Use multiple times to bypass increasingly more confirmation prompts. "
    "Dangerous option. Not recommended.",
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
@profile
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
    bypass_prompt: BypassPromptLevel,
    dfs: bool,
    bfs: bool,
    separate_class_and_function: bool,
) -> None:
    """A command line utility to sort Python source code by abstraction levels"""

    options = SimpleNamespace(**ctx.params)
    validate_args(options)

    if not no_aggressive:
        # Optionally use uvloop to boost speed
        try:
            import uvloop  # type: ignore

            uvloop.install()
        except ImportError:
            pass

    # First confirmation prompt
    if BypassPromptLevel.NO < bypass_prompt < BypassPromptLevel.HIGH:
        ans = click.confirm(
            "Are you sure you want to bypass all confirmation prompts? "
            "(Dangerous, not recommended)"
        )
        if not ans:
            bypass_prompt = BypassPromptLevel.NO

    # Second confirmation prompt
    if BypassPromptLevel.NO < bypass_prompt < BypassPromptLevel.MEDIUM:
        ans = click.confirm(
            "Are you REALLY REALLY REALLY sure you want to bypass all confirmation prompts? "
            "(Dangerous, not recommended)"
        )
        if not ans:
            bypass_prompt = BypassPromptLevel.NO

    files = list(collect_python_files(filepaths))
    if not files:
        print("No file is found")
        return
    print(f"Found {len(files)} files")

    format_option = FormatOption(
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
    """Preliminary check of the validness of the CLI argument"""

    # FIXME use click library's builtin mechanism to specify mutually exclusive options

    if sum([options.check, options.display_diff, options.in_place]) > 1:
        raise MutuallyExclusiveOptions(
            "Only one of the `--check`, `--diff` and `--in-place` options can be specified at the same time"
        )

    if options.quiet and options.verbose:
        raise MutuallyExclusiveOptions(
            "Can't specify both `--quiet` and `--verbose` options"
        )

    if options.dfs and options.bfs:
        raise MutuallyExclusiveOptions("Can't specify both `--dfs` and `--bfs` options")

    if options.in_place and options.quiet:
        # Because in-place updating files requires user confirmation through command line prompts.
        raise MutuallyExclusiveOptions(
            "Can't specify both `--in-place` and `--quiet` options"
        )


# TODO use multi-thread to accelerate
def collect_python_files(filepaths: Iterable[str]) -> Iterator[str]:
    """Yield python files searched from the given paths"""

    for filepath in filepaths:
        filepath = Path(filepath)

        if not filepath.exists():
            print(f'File "{filepath}" doesn\'t exist. Skipped.', file=sys.stderr)

        elif filepath.is_file():

            # We don't test file suffix, because it's possible user explicitly enters an
            # input file that contains Python code but doesn't have `.py` extension.
            # If it doesn't contain Python code, a SyntaxError will be raised from other
            # part of the code and handled by exception handling routines anyway.
            yield str(filepath)

        elif filepath.is_dir():
            for fp in filepath.rglob("*.py"):
                yield str(fp)

        else:
            raise NotImplementedError


def absort_files(
    files: list[str],
    encoding: str = "utf-8",
    bypass_prompt: BypassPromptLevel = BypassPromptLevel.NO,
    verbose: bool = False,
    file_action: FileAction = FileAction.PRINT,
    py_version: PyVersion = sys.version_info[:2],
    comment_strategy: CommentStrategy = CommentStrategy.ATTR_FOLLOW_DECL,
    format_option: FormatOption = FormatOption(),
    sort_order: SortOrder = SortOrder.TOPOLOGICAL,
) -> Counter[FileResult]:
    """Sort a list of files"""

    # TODO use multi-processing to boost speed of handling a bunch of files (CPU-bound parts)

    async def entry() -> Counter[FileResult]:
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
        results = await asyncio.gather(*tasks)
        return Counter(results)

    return asyncio.run(entry())


@profile
async def absort_file(
    file: str,
    encoding: str = "utf-8",
    bypass_prompt: BypassPromptLevel = BypassPromptLevel.NO,
    verbose: bool = False,
    file_action: FileAction = FileAction.PRINT,
    py_version: PyVersion = sys.version_info[:2],
    comment_strategy: CommentStrategy = CommentStrategy.ATTR_FOLLOW_DECL,
    format_option: FormatOption = FormatOption(),
    sort_order: SortOrder = SortOrder.TOPOLOGICAL,
) -> FileResult:
    """Sort the source in the given file"""

    async def read_source(filepath: Path) -> str:
        """Read source from the file, including exception handling"""

        try:
            return await asyncio.to_thread(filepath.read_text, encoding)
        except UnicodeDecodeError:
            print(f"{filepath} is not decodable by {encoding}", file=sys.stderr)
            print(f"Try to automatically detect file encoding......", file=sys.stderr)
            binary = await asyncio.to_thread(filepath.read_bytes)
            detected_encoding = cchardet.detect(binary)["encoding"]

            try:
                return await asyncio.to_thread(filepath.read_text, detected_encoding)
            except UnicodeDecodeError:

                print(f"{filepath} has unknown encoding.", file=sys.stderr)
                raise ABSortFail

    def absort_source(old_source: str) -> str:
        """Sort the source in string, including exception handling"""

        try:
            return absort_str(
                old_source, py_version, comment_strategy, format_option, sort_order
            )
        except SyntaxError as exc:
            # if re.fullmatch(r"Missing parentheses in call to 'print'. Did you mean print(.*)\?", exc.msg):
            #     pass
            print(f"{filepath} has erroneous syntax: {exc.msg}", file=sys.stderr)
            raise ABSortFail

        except NameRedefinition:
            print(
                f"{filepath} contains duplicate name redefinitions. Not supported yet.",
                file=sys.stderr,
            )
            raise ABSortFail

    async def write_source(filepath: Path, new_source: str) -> FileResult:
        """Write the new source to the file, prompt for confirmation and make backup"""

        if bypass_prompt < BypassPromptLevel.LOW:
            ans = click.confirm(
                f"Are you sure you want to in-place update the file {filepath}?"
            )
            if not ans:
                return FileResult.UNMODIFIED

        async with CACHE_DIR_LOCK:
            await backup_to_cache(filepath)

        await asyncio.to_thread(filepath.write_text, new_source, encoding)
        if verbose:
            print(bright_green(f"Processed {filepath}"))
        return FileResult.MODIFIED

    async def process_new_source(new_source: str, filepath: Path) -> FileResult:
        """Process the new source as specified by the CLI arguments"""

        # TODO add more styled output (e.g. colorized)

        if file_action is FileAction.DIFF:

            display_diff_with_filename(old_source, new_source, str(filepath))
            return FileResult.UNMODIFIED

        elif file_action is FileAction.WRITE:

            if old_source == new_source:
                return FileResult.UNMODIFIED
            return await write_source(filepath, new_source)

        elif file_action is FileAction.CHECK:

            if old_source != new_source:
                print(f"{filepath} needs reformat")
            return FileResult.UNMODIFIED

        elif file_action is FileAction.PRINT:
            divider = bright_yellow("-" * 79)
            print(divider)
            print(filepath)
            print(divider)
            print(new_source)
            print(divider)
            print("\n", end="")

            return FileResult.UNMODIFIED

        else:
            raise ValueError("the file_action argument receives invalid value")

    try:

        filepath = Path(file)
        old_source = await read_source(filepath)
        new_source = absort_source(old_source)
        return await process_new_source(new_source, filepath)

    except ABSortFail:
        return FileResult.FAILED


async def backup_to_cache(file: Path) -> None:
    """Make a backup of the file, put in the cache"""

    def generate_timestamp() -> str:
        now = str(datetime.now())
        digits = (char for char in now if char.isdigit())
        return "".join(take(14, digits))

    timestamp = generate_timestamp()
    backup_file = CACHE_DIR / (file.name + "." + timestamp + ".backup")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    readme = CACHE_DIR / "README"
    if not readme.exists():
        await asyncio.to_thread(
            readme.write_text,
            "This directory is a cache folder of the absort utility (https://github.com/MapleCCC/ABSort). "
            "It's used for precautious recovery purpose. It can be removed safely.",
            encoding="utf-8",
        )

    shutil.copy2(file, backup_file)

    if CACHE_DIR.stat().st_size > CACHE_MAX_SIZE:
        await shrink_cache()


async def shrink_cache() -> None:
    """Shrink the size of cache to under threshold"""

    shrink_target_size = CACHE_MAX_SIZE - CACHE_DIR.stat().st_size

    backup_filename_pattern = r".*\.(?P<timestamp>\d{14})\.backup"

    total_size = 0
    pq = PriorityQueue(reverse=True)  # type: PriorityQueue[Path]

    for file in CACHE_DIR.iterdir():
        m = re.fullmatch(backup_filename_pattern, file.name)
        if not m:
            continue

        timestamp = m.group("timestamp")
        pq.push(file, priority=timestamp)

        total_size += file.stat().st_size

        while pq and total_size - pq.top().stat().st_size >= shrink_target_size:
            total_size -= pq.top().stat().st_size

    for file in pq.to_iterator():
        file.unlink()


def display_diff_with_filename(
    old_src: str, new_src: str, filename: str = None
) -> None:
    """Display diff view between old source and new source"""

    old_src_lines = old_src.splitlines(keepends=True)
    new_src_lines = new_src.splitlines(keepends=True)

    fromfile = "old/" + filename if filename else ""
    tofile = "new/" + filename if filename else ""

    diff_view_lines = colorized_unified_diff(
        old_src_lines, new_src_lines, fromfile, tofile
    )

    print(*diff_view_lines, sep="", end="")
    print("\n", end="")


def display_summary(digest: Counter[FileResult]) -> None:
    """Display the succint summary of the sorting process"""

    summary = []
    for file_result, count in digest.items():
        if not count:
            continue
        plurality_suffix = "s" if count > 1 else ""
        summary.append(f"{count} file{plurality_suffix} {file_result.value}")
    print(", ".join(summary) + ".")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
