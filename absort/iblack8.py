#!/usr/bin/env python3

from functools import partial
from pathlib import Path
from typing import Any, Iterable, cast

import autopep8
import black
import click
import isort

# Alternatively we can name it autoiblack, iblack8


class VersionIncompatibleError(Exception):
    pass


def hasattrs(obj: Any, names: Iterable[str]) -> bool:
    return all(map(partial(hasattr, obj), names))


# FIXME Change to black's public interface after black publishes the first
# stable release in the future.
if not hasattrs(black, ["format_str", "FileMode"]):
    raise VersionIncompatibleError("black version incompatible")

autopep8_options = {"aggressive": 2, "select": ["E501"]}


def format_code(s: str) -> str:
    fixed = autopep8.fix_code(s, options=autopep8_options)

    sorted_ = isort.code(fixed)

    # to inform the type checker that sorted_ is of str type
    sorted_ = cast(str, sorted_)

    formatted = black.format_str(sorted_, mode=black.FileMode())

    return formatted


@click.command()
@click.argument("filename")
def main(filename: str) -> None:
    p = Path(filename)
    content = p.read_text(encoding="utf-8")
    formatted = format_code(content)
    p.write_text(formatted, encoding="utf-8")


if __name__ == "__main__":
    main()
