import ast
import operator
from pathlib import Path
from typing import Any, Callable

from absort.__main__ import NameRedefinition, absort_str
from absort.ast_utils import ast_deep_equal


# Use third-party library hypothesmith to generate random valid Python source code, to
# conduct property-based testing on the absort*() interface.
# The guy who use such tool to test on black library and CPython stdlib and report issues is Zac-HD (https://github.com/Zac-HD).


TEST_DATA_DIR = Path(__file__).with_name("data")


def contains(
    container: Any, elem: Any, equal: Callable[[Any, Any], bool] = operator.eq
) -> bool:
    return any(equal(elem, value) for value in container)


def test_absort_str() -> None:
    for test_sample in TEST_DATA_DIR.iterdir():
        if test_sample.suffix == ".py":
            try:
                source = test_sample.read_text(encoding="utf-8")
                new_source = absort_str(source)

                old_ast = ast.parse(source)
                new_ast = ast.parse(new_source)

                assert len(old_ast.body) == len(new_ast.body)
                for stmt in old_ast.body:
                    assert contains(new_ast.body, stmt, equal=ast_deep_equal)
            except (SyntaxError, NameRedefinition):
                pass
