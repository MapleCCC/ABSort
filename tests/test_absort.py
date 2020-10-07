import ast
import operator
from typing import Any, Callable

from hypothesis import given, settings, HealthCheck
from hypothesmith import from_grammar, from_node

from absort.__main__ import absort_str
from absort.ast_utils import ast_equal


# Use third-party library hypothesmith to generate random valid Python source code, to
# conduct property-based testing on the absort*() interface.
# The guy who use such tool to test on black library and CPython stdlib and report issues is Zac-HD (https://github.com/Zac-HD).


def contains(
    container: Any, elem: Any, equal: Callable[[Any, Any], bool] = None
) -> bool:
    if equal is None:
        equal = operator.eq

    for value in container:
        if equal(elem, value):
            return True
    return False


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(from_grammar())
# @given(from_node())
def test_absort_str(source: str) -> None:
    new_source = absort_str(source)

    old_ast = ast.parse(source)
    new_ast = ast.parse(new_source)

    assert len(old_ast.body) == len(new_ast.body)
    for stmt in old_ast.body:
        assert contains(new_ast.body, stmt, equal=ast_equal)
