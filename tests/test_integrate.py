import random
import sys
from itertools import product
from pathlib import Path
from shutil import copy2

from click.testing import CliRunner
from more_itertools import collapse

from absort.__main__ import MutuallyExclusiveOptions, main as absort_entry


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
        for test_file in TEST_FILES:
            filename = test_file.name
            copy2(test_file, Path.cwd() / filename)

            option = random.choice(option_combinations)
            result = runner.invoke(
                absort_entry,
                [str(filename), *option],
            )

            if isinstance(result.exception, MutuallyExclusiveOptions):
                continue
            assert result.exit_code == 0

            # TODO add more asserts
