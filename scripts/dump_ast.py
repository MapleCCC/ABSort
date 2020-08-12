#!/usr/bin/env python3

import ast
import io

import click

from ast_utils import ast_pretty_dump


@click.command()
@click.argument("file", type=click.File("r", encoding="utf-8"))
def main(file: io.TextIOWrapper) -> None:
    print(ast_pretty_dump(ast.parse(file.read())))


if __name__ == "__main__":
    main()
