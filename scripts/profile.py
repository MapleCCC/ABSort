#!/usr/bin/env python3

import ast
import subprocess
import sys
from pathlib import Path
from shutil import copy2
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory

from absort.exceptions import Unreachable


STDLIB_DIR = Path(sys.executable).with_name("Lib")
ISORT_SRC_DIR = STDLIB_DIR / "site-packages" / "isort"

# TEST_FILES = ISORT_SRC_DIR.rglob("*.py")
TEST_FILES = STDLIB_DIR.rglob("*.py")

ENTRY_SCRIPT_NAME = "__main__.py"

PROFILE_RESULT_OUTPUT_FILE = Path("line-profiler-output.txt")


class RelativeImportTransformer(ast.NodeTransformer):
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        if node.level is None:
            return node

        if node.level > 0:
            node.level -= 1
        elif node.level == 0:
            pass
        else:
            raise Unreachable

        return node


class AddProfileDecoratorToClassMethodTransformer(ast.NodeTransformer):
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        def add_profile_decorator(node: ast.stmt) -> ast.stmt:
            if isinstance(node, ast.FunctionDef):
                node.decorator_list.append(ast.Name("profile", ast.Load()))
            return node

        node = self.generic_visit(node)  # type: ignore

        criteria = (
            lambda decorator: isinstance(decorator, ast.Name)
            and decorator.id == "add_profile_decorator_to_class_methods"
        )
        if any(map(criteria, node.decorator_list)):
            node.body = list(map(add_profile_decorator, node.body))

        return node


def preprocess(p: Path) -> None:
    old_content = p.read_text(encoding="utf-8")

    try:
        tree = ast.parse(old_content)
    except SyntaxError as exc:
        raise ValueError(f"{p} has erroneous syntax: {exc.msg}")

    new_tree = RelativeImportTransformer().visit(tree)
    new_tree = AddProfileDecoratorToClassMethodTransformer().visit(tree)

    new_tree = ast.fix_missing_locations(new_tree)

    new_content = ast.unparse(new_tree)

    p.write_text(new_content, encoding="utf-8")


def main() -> None:
    with TemporaryDirectory() as d:
        tempdir = Path(d)

        for f in Path("absort").rglob("*.py"):
            target = tempdir / f.name
            copy2(f, target)
            preprocess(target)

        print("Preprocessing is completed")

        entry_script = tempdir / ENTRY_SCRIPT_NAME

        completed_proc = subprocess.run(
            [
                "time",
                "kernprof",
                "--line-by-line",
                "--view",
                "--builtin",
                str(entry_script),
                "--quiet",
                *TEST_FILES,
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
            PROFILE_RESULT_OUTPUT_FILE.write_text(stdout, encoding="utf-8")
            print(f"Profile result data is written to {PROFILE_RESULT_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
