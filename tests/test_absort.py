import ast
import os
import random
import re
import sys
from itertools import combinations_with_replacement, product
from pathlib import Path

import attr

from absort.__main__ import CommentStrategy, FormatOption, NameRedefinition, absort_str
from absort.ast_utils import ast_deep_equal
from absort.utils import contains


# Use third-party library hypothesmith to generate random valid Python source code, to
# conduct property-based testing on the absort*() interface.
# The guy who use such tool to test on black library and CPython stdlib and report issues is Zac-HD (https://github.com/Zac-HD).


STDLIB_DIR = Path(sys.executable).with_name("Lib")

# Reference: https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
if os.getenv("CI") and os.getenv("TRAVIS"):
    py_version = os.getenv("TRAVIS_PYTHON_VERSION")
    assert py_version
    # Reference: https://docs.travis-ci.com/user/languages/python/#python-versions
    # Reference: https://docs.travis-ci.com/user/languages/python/#development-releases-support
    py_version_num = re.fullmatch(r"(?P<num>[0-9.]+)(?:-dev)?", py_version).group("num")
    STDLIB_DIR = Path(f"/opt/python/{py_version}/lib/python{py_version_num}/")


TEST_FILES = STDLIB_DIR.rglob("*.py")


def test_absort_str() -> None:
    all_comment_strategies = iter(CommentStrategy)
    format_option_init_arg_options = combinations_with_replacement(
        (True, False), len(attr.fields(FormatOption))
    )
    all_format_options = (
        FormatOption(*c) for c in format_option_init_arg_options  # type: ignore
    )
    all_arg_options = list(product(all_comment_strategies, all_format_options))

    for test_sample in TEST_FILES:
        try:
            source = test_sample.read_text(encoding="utf-8")
            arg_option = random.choice(all_arg_options)
            comment_strategy, format_option = arg_option
            new_source = absort_str(
                source,
                comment_strategy=comment_strategy,
                format_option=format_option,
            )

            old_ast = ast.parse(source)
            new_ast = ast.parse(new_source)

            assert len(old_ast.body) == len(new_ast.body)
            for stmt in old_ast.body:
                assert contains(new_ast.body, stmt, equal=ast_deep_equal)
        except (SyntaxError, NameRedefinition):
            pass
