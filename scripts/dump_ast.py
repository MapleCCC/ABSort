#!/usr/bin/env python3

import ast
import io
import os
import sys

import click

sys.path.append(os.getcwd())
from absort.astutils import ast_pretty_dump


@click.command()
@click.argument("file", type=click.File("r", encoding="utf-8"))
@click.option("-c", "--compact", "compact", is_flag=True, default=False)
def main(file: io.TextIOWrapper, compact: bool) -> None:
    print(ast_pretty_dump(ast.parse(file.read()), annotate_fields=not compact))


if __name__ == "__main__":
    main()
