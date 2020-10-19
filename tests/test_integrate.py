import ast
import random
import sys
from itertools import product
from pathlib import Path
from shutil import copy2

from click.testing import CliRunner
from more_itertools import collapse

from absort.__main__ import MutuallyExclusiveOptions, main as absort_entry
from absort.ast_utils import ast_deep_equal
from absort.utils import contains


STDLIB_DIR = Path(sys.executable).with_name("Lib")
TEST_FILES = STDLIB_DIR.rglob("*.py")


def test_integrate() -> None:
    file_action_options = [[], "--check", "--diff", ["--in-place", "-yyy"]]
    format_flags = [
        "--no-fix-main-to-bottom",
        "--reverse",
        "--no-aggressive",
        "--separate-class-and-function",
    ]
    format_options = product(*([[], flag] for flag in format_flags))
    sort_order_options = [[], "--dfs", "--bfs"]
    verboseness_options = [[], "--quiet", "--verbose"]
    miscellaneous_options = [[], "--color-off"]
    comment_strategy_options = [
        [],
        ["--comment-strategy", "attr-follow-decl"],
        ["--comment-strategy", "push-top"],
        ["--comment-strategy", "ignore"],
    ]
    option_combinations = [
        list(collapse(p))
        for p in product(
            file_action_options,
            format_options,
            sort_order_options,
            verboseness_options,
            miscellaneous_options,
            comment_strategy_options,
        )
    ]

    runner = CliRunner()
    with runner.isolated_filesystem():
        for source_test_file in TEST_FILES:
            test_file = Path.cwd() / source_test_file.name
            copy2(source_test_file, test_file)

            old_content = test_file.read_text(encoding="utf-8")

            option = random.choice(option_combinations)
            result = runner.invoke(absort_entry, [str(test_file), *option])

            if isinstance(result.exception, MutuallyExclusiveOptions):
                continue

            assert result.exit_code == 0

            if "--in-place" in option:
                old_tree = ast.parse(old_content)
                new_content = test_file.read_text(encoding="utf-8")
                new_tree = ast.parse(new_content)
                assert len(new_tree.body) == len(old_tree.body)
                for stmt in new_tree.body:
                    assert contains(old_tree.body, stmt, equal=ast_deep_equal)

            # TODO add more asserts
