import ast
import os
import re
import sys
from itertools import product
from pathlib import Path
from shutil import copy2

from click.testing import CliRunner
from hypothesis import given, settings
from hypothesis.strategies import sampled_from
from more_itertools import collapse

from absort.__main__ import MutuallyExclusiveOptions, main as absort_entry
from absort.ast_utils import ast_deep_equal
from absort.utils import constantfunc, contains

from .strategies import products


STDLIB_DIR = Path(sys.executable).with_name("Lib")

# Reference: https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
if os.getenv("CI") and os.getenv("TRAVIS"):
    py_version = os.getenv("TRAVIS_PYTHON_VERSION")
    assert py_version

    # Reference: https://docs.travis-ci.com/user/languages/python/#python-versions
    # Reference: https://docs.travis-ci.com/user/languages/python/#development-releases-support
    py_version_num = re.fullmatch(r"(?P<num>[0-9.]+)(?:-dev)?", py_version).group("num")

    STDLIB_DIR = Path(f"/opt/python/{py_version}/lib/python{py_version_num}/")


TEST_FILES = list(STDLIB_DIR.rglob("*.py"))


file_action_options = [[], "--check", "--diff", ["--in-place", "-yyy"]]
format_flags = [
    "--no-fix-main-to-bottom",
    "--reverse",
    "--no-aggressive",
    "--separate-class-and-function",
]
format_options = list(product(*([[], flag] for flag in format_flags)))
sort_order_options = [[], "--dfs", "--bfs"]
verboseness_options = [[], "--quiet", "--verbose"]
miscellaneous_options = [[], "--color-off"]
comment_strategy_options = [
    [],
    ["--comment-strategy", "attr-follow-decl"],
    ["--comment-strategy", "push-top"],
    ["--comment-strategy", "ignore"],
]
cli_options = constantfunc(
    products(
        file_action_options,
        format_options,
        sort_order_options,
        verboseness_options,
        miscellaneous_options,
        comment_strategy_options,
    )
    .map(collapse)
    .map(tuple)
)


@given(sampled_from(TEST_FILES), cli_options())
@settings(deadline=None)
def test_integrate(source_test_file: Path, option: tuple[str, ...]) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        test_file = Path.cwd() / source_test_file.name
        copy2(source_test_file, test_file)

        old_content = test_file.read_text(encoding="utf-8")

        result = runner.invoke(absort_entry, [*option, "--", str(test_file)])

        if isinstance(result.exception, MutuallyExclusiveOptions):
            return

        assert result.exit_code == 0

        if "--in-place" in option:
            old_tree = ast.parse(old_content)
            new_content = test_file.read_text(encoding="utf-8")
            new_tree = ast.parse(new_content)

            assert len(new_tree.body) == len(old_tree.body)
            for stmt in new_tree.body:
                assert contains(old_tree.body, stmt, equal=ast_deep_equal)

        # TODO add more asserts
