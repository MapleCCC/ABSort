from collections.abc import Iterable
from itertools import tee

from hypothesis import assume, given
from hypothesis.strategies import (
    DrawFn,
    characters,
    composite,
    from_regex,
    integers,
    iterables,
    lists,
    permutations,
    sampled_from,
)

from absort.utils import iequal, strict_splitlines
from recipes.string import line_boundaries


# TODO add more tests for various utils


@given(iterables(integers(), max_size=1000), integers(min_value=2, max_value=100))
def test_iequal_equal(iterable: Iterable[int], length: int) -> None:
    iterables = tee(iterable, length)
    assert iequal(*iterables, strict=True)


@given(lists(iterables(integers(), max_size=1000), min_size=2))
def test_iequal_unequal(iterables: list[Iterable[int]]) -> None:
    ls = set((*iterable,) for iterable in iterables)
    assume(len(ls) > 1)
    new_iterables = map(iter, ls)
    assert not iequal(*new_iterables, strict=True)


@given(from_regex(r"[a-zA-Z0-9_\n]*", fullmatch=True))
def test_strict_splitlines_newline_only(s: str) -> None:
    assert strict_splitlines(s) == s.splitlines()
    assert strict_splitlines(s, keepends=True) == s.splitlines(keepends=True)


@composite
def text_containing_universal_newlines(draw: DrawFn) -> str:
    a = draw(lists(characters()))
    b = draw(lists(sampled_from(special_line_boundaries), min_size=1))
    return "".join(draw(permutations(a + b)))


special_line_boundaries = list(set(line_boundaries) - {"\n"})
pat = "|".join(f"({s})" for s in special_line_boundaries)

# XXX Use `--hypothesis-show-statistics` to find out which approach to generate test
# data is better.

@given(text_containing_universal_newlines())
# @given(from_regex(rf"(.*({pat}))+.*"))
def test_strict_splitlines_universal_newline(s: str) -> None:
    assert strict_splitlines(s) != s.splitlines()
    # assert strict_splitlines(s, keepends=True) != s.splitlines(keepends=True)
