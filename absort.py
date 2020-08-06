#!/usr/bin/env python3

import atexit
import ast
import re
from pathlib import Path
from pprint import PrettyPrinter
from tempfile import TemporaryDirectory
from typing import List, Set, Union

import astor
import click
from pylint import epylint

pprint = PrettyPrinter().pprint


DECL_STMT_CLASSES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TYPE_DECL_STMT = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def get_dependency_of_decl(decl: TYPE_DECL_STMT) -> Set[str]:
    src = astor.to_source(decl)
    deps = set()
    with TemporaryDirectory() as tempdir:
        tempfile = Path(tempdir) / "file.py"
        tempfile.write_text(src, encoding="utf-8")
        lint_stdout, lint_stderr = epylint.py_run(str(tempfile), return_std=True)  # type: ignore
        out = lint_stdout.read()
        err = lint_stderr.read()
        assert not err
        for line in out.splitlines():
            m = re.fullmatch(
                r".*: error \(E0602, undefined-variable, (?P<declname>\w+)\) Undefined variable '(?P<dependency>\w+)'",
                line,
            )
            if m:
                deps.add(m.group("dependency"))
        return deps


def absort_decls(decls: List[TYPE_DECL_STMT]) -> List[TYPE_DECL_STMT]:
    infos = {}
    for decl in decls:
        infos[decl] = get_dependency_of_decl(decl)
    return []


@click.command()
@click.argument("file")
def main(file: str) -> None:
    content = Path(file).read_text(encoding="utf-8")
    tree = ast.parse(content)

    top_level_stmts = tree.body

    decls = [stmt for stmt in top_level_stmts if isinstance(stmt, DECL_STMT_CLASSES)]
    decl_names = [decl.name for decl in decls]
    if len(decl_names) != len(set(decl_names)):
        raise ValueError("Name redefinition exists. Not supported yet.")

    new_stmts = []
    buffer = []
    for stmt in top_level_stmts:
        if isinstance(stmt, DECL_STMT_CLASSES):
            buffer.append(stmt)
        else:
            if buffer:
                new_stmts.extend(absort_decls(buffer))
                buffer.clear()
            new_stmts.append(stmt)
    if buffer:
        new_stmts.extend(absort_decls(buffer))
        buffer.clear()


if __name__ == "__main__":
    main()
