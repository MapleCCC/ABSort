from __future__ import annotations

import ast
import os
import re
import sys
from itertools import product
from pathlib import Path

import attr
from hypothesis import given, settings
from hypothesis.strategies import sampled_from

from absort.__main__ import (
    CommentStrategy,
    FormatOption,
    NameRedefinition,
    SortOrder,
    absort_str,
)
from absort.ast_utils import ast_deep_equal
from absort.utils import constantfunc, contains

from .strategies import products


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


TEST_FILES = list(STDLIB_DIR.rglob("*.py"))


@attr.s(auto_attribs=True)
class Option:
    comment_strategy: CommentStrategy
    format_option: FormatOption
    sort_order: SortOrder

    @classmethod
    def from_tuple(cls: type, tup: tuple) -> Option:
        return cls(*tup)


all_comment_strategies = list(CommentStrategy)
all_format_options = [
    FormatOption(*p)  # type: ignore
    for p in product(*([(True, False)] * len(attr.fields(FormatOption))))
]
all_sort_orders = list(SortOrder)

arg_options = constantfunc(
    products(all_comment_strategies, all_format_options, all_sort_orders).map(
        Option.from_tuple
    )
)


@given(sampled_from(TEST_FILES), arg_options())
@settings(deadline=None)
def test_absort_str(test_sample: Path, option: Option) -> None:
    try:
        source = test_sample.read_text(encoding="utf-8")
        new_source = absort_str(source, **attr.asdict(option, recurse=False))

        second_run_new_source = absort_str(source, **attr.asdict(option, recurse=False))
        # Check that absort is deterministic and stable
        assert new_source == second_run_new_source

        old_ast = ast.parse(source)
        new_ast = ast.parse(new_source)

        assert len(old_ast.body) == len(new_ast.body)
        for stmt in old_ast.body:
            assert contains(new_ast.body, stmt, equal=ast_deep_equal)
    except (SyntaxError, NameRedefinition, UnicodeDecodeError):
        pass
    except Exception as exc:
        exc_cls_name = getattr(exc.__class__, "__name__", "some exception")
        print(f"Encountered {exc_cls_name} when sorting {test_sample}")
        raise


# TODO add unit test for absort_file()
# TODO add unit test for absort_files()
