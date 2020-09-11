#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import time
from functools import singledispatch
from pathlib import Path
from typing import Any, Callable, List, Sequence, Type, TypeVar

import click
import semver
from github import Github

sys.path.append(os.getcwd())
from absort.__version__ import __version__ as current_version
from absort.utils import Logger
from scripts._local_credentials import github_account_access_token


logger = Logger()


def bump_file(file: str, pattern: str, repl: str) -> None:
    p = Path(file)
    old_content = p.read_text(encoding="utf-8")
    new_content, num_of_sub = re.subn(pattern, repl, old_content)
    if not num_of_sub:
        logger.log(
            f"Can't find match of pattern {pattern} in file {file}", file=sys.stderr
        )
        return
    p.write_text(new_content, encoding="utf-8")


def bump_file___version__(new_version: str) -> None:
    pattern = r"__version__\s*=\s*\"(.*)\""
    repl = f'__version__ = "{new_version}"'
    bump_file("absort/__version__.py", pattern, repl)


def bump_file_README(new_version: str) -> None:
    pattern = r"github.com/MapleCCC/ABSort/compare/.*\.\.\.master"
    repl = f"github.com/MapleCCC/ABSort/compare/{new_version}...master"
    bump_file("README.md", pattern, repl)

    pattern = r"git\+https://github\.com/MapleCCC/ABSort\.git@.*#egg=ABSort"
    repl = f"git+https://github.com/MapleCCC/ABSort.git@{new_version}#egg=ABSort"
    bump_file("README.md", pattern, repl)


def run(cmd: Sequence[str]) -> None:
    subprocess.run(cmd).check_returncode()


def contains_uncommitted_change(filepath: str):
    # Add non-existent file check/guard, because `git status --porcelain` has
    # similar output for both unmodified file and non-existent file
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Can't get status of non-existent file: {filepath}")

    cmpl_proc = subprocess.run(
        ["git", "status", "--porcelain", "--no-renames", "--", filepath],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if cmpl_proc.returncode != 0:
        raise RuntimeError(f"Error getting status of {filepath}")

    return len(cmpl_proc.stdout) != 0


class MaxRetryError(Exception):
    pass


_T = TypeVar("_T")


@singledispatch
def retry(
    total: int = 3, backoff_factor: float = 0.1, on_except: List[Type[Exception]] = None
) -> Callable[..., _T]:
    """
    The `total` and `backoff_factor` parameters has same meaning with that of
    `urllib3.util.Retry` (https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.Retry)
    """

    if total < 0 or backoff_factor < 0:
        raise ValueError(
            "`total` and `backoff_factor` parameters should have values that are non-negative number."
        )

    if on_except is None:
        exceptions = Exception
    else:
        exceptions = tuple(on_except)

    def apply(fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        for i in range(total + 1):
            if i >= 2:
                time.sleep(backoff_factor * (2 ** (i - 1)))
            try:
                return fn(*args, **kwargs)
            except exceptions:
                continue
        raise MaxRetryError(
            f"Reached maximum retries on applying function {fn} to arguments {args}, {kwargs}"
        )

    return apply


@retry.register
def _(fn: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
    base = retry.registry[object]
    return base()(fn, *args, **kwargs)


@click.command()
@click.argument("component")
@click.option("--no-release", is_flag=True)
def main(component: str, no_release: bool) -> None:
    if contains_uncommitted_change("README.md"):
        raise RuntimeError(
            "README.md contains uncommitted change. "
            "Please clean it up before rerun the script."
        )

    logger.log("Calculating new version......")

    old_version_info = semver.VersionInfo.parse(current_version.lstrip("v"))

    method = getattr(old_version_info, f"bump_{component}", None)
    if method is None:
        raise ValueError(
            "Invalid value for argument `component`. "
            "Valid values are `major`, `minor`, `patch`, and `prerelease`."
        )
    new_version_info = method()

    new_version = "v" + str(new_version_info)

    logger.log("Bump the __version__ variable in __version__.py ......")
    bump_file___version__(new_version)

    logger.log("Bump version-related information in README.md ......")
    bump_file_README(new_version)

    run(["git", "add", "absort/__version__.py"])

    run(["git", "add", "README.md"])

    logger.log("Committing the special commit for bumping version......")
    run(["git", "commit", "-m", f"Bump version to {new_version}"])

    logger.log("Creating tag for new version......")
    run(["git", "tag", "-d", new_version])
    run(["git", "tag", new_version])

    # TODO if we change from using subprocess.run to using PyGithub,
    # will the time cost be shorter?
    logger.log("Pushing tag to remote......")
    retry(run, ["git", "push", "origin", new_version])

    if not no_release:
        logger.log("Creating release in GitHub repo......")

        # TODO when releasing, put in the message about what's updated, what's fixed,
        # and the hash signature of the assets.

        # Create release in GitHub. Upload the zip archive as release asset.
        g = Github(github_account_access_token)
        repo = g.get_repo("MapleCCC/ABSort")
        retry(
            repo.create_git_release,
            tag=new_version,
            name=new_version,
            message="For detail changelog, please consult commit history, and commit messages.",
        )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
