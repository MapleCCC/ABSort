#!/usr/bin/env python3

import re
import subprocess
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

ISORT_MAIN_FILEPATH = "D:/Program Files/Python38/Lib/site-packages/isort/main.py"


# FIXME it's possible for current implementation to accidentally transform the relative
# import that is not actually relative import. For example, a relative import embedded
# in a string literal. The only robust and correct way to avoid such problem is to
# construct syntax tree using lexical analysis and syntax analysis.
def transform_relative_imports(p: Path) -> None:
    old_content = p.read_text(encoding="utf-8")
    pattern = r"from \.(?P<module>\w*) import (?P<names>.*)"
    repl = r"from \g<module> import \g<names>"
    new_content = re.sub(pattern, repl, old_content)
    p.write_text(new_content, encoding="utf-8")


def main() -> None:
    with TemporaryDirectory() as d:
        tempdir = Path(d)

        for f in Path("absort").rglob("*.py"):
            target = tempdir / f.name
            copy2(f, target)
            transform_relative_imports(target)

        entry_script = tempdir / "__main__.py"

        completed_proc = subprocess.run(
            ["kernprof", "-l", "-v", str(entry_script), "--quiet", ISORT_MAIN_FILEPATH],
            encoding="utf-8",
            # WARNING: don't specify capture_output if stderr or stdout is specified
            # Combine stdout and stderr into one stream
            stderr=subprocess.STDOUT,
        )
        completed_proc.check_returncode()
        print(completed_proc.stdout)


if __name__ == "__main__":
    main()
