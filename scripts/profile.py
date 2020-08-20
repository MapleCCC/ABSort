#!/usr/bin/env python3

import ast
import subprocess
from pathlib import Path
from shutil import copy2
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory

import astor

ISORT_MAIN_FILEPATH = "D:/Program Files/Python38/Lib/site-packages/isort/main.py"
ENTRY_SCRIPT_NAME = "__main__.py"
PROFILE_RESULT_OUTPUT_FILE = "line-profiler-output.txt"


def transform_relative_imports(p: Path) -> None:
    class RelativeImportTransformer(ast.NodeTransformer):
        def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
            if node.level is None:
                return node

            if node.level > 0:
                node.level -= 1
            elif node.level == 0:
                pass
            else:
                raise RuntimeError("Unreachable")

            return node

    old_content = p.read_text(encoding="utf-8")

    try:
        tree = ast.parse(old_content)
    except SyntaxError as exc:
        raise ValueError(f"{p} has erroneous syntax: {exc.msg}")

    new_tree = RelativeImportTransformer().visit(tree)
    new_tree = ast.fix_missing_locations(new_tree)

    new_content = astor.to_source(new_tree)

    p.write_text(new_content, encoding="utf-8")


def main() -> None:
    with TemporaryDirectory() as d:
        tempdir = Path(d)

        for f in Path("absort").rglob("*.py"):
            target = tempdir / f.name
            copy2(f, target)
            transform_relative_imports(target)

        entry_script = tempdir / ENTRY_SCRIPT_NAME

        completed_proc = subprocess.run(
            [
                "time",
                "kernprof",
                "--line-by-line",
                "--view",
                "--builtin",
                "--outfile",
                PROFILE_RESULT_OUTPUT_FILE,
                str(entry_script),
                "--quiet",
                ISORT_MAIN_FILEPATH,
            ],
            encoding="utf-8",
            # WARNING: don't specify capture_output if stderr or stdout is specified
            capture_output=True,
        )
        stdout = completed_proc.stdout
        stderr = completed_proc.stderr
        try:
            completed_proc.check_returncode()
        except CalledProcessError:
            print("Profile failed.")
            print(stderr)
        else:
            print("Profile result data is written to line-profiler-output.txt")


if __name__ == "__main__":
    main()
