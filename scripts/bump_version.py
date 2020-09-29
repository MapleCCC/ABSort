#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import time
from functools import partial
from pathlib import Path
from typing import Callable, List, Sequence, Type, TypeVar

import click
import semver
from github import Github

sys.path.append(os.getcwd())
from absort.__version__ import __version__ as current_version
from absort.utils import Logger
from scripts._local_credentials import github_account_access_token


_T = TypeVar("_T")


FILES_TO_UPDATE = ["README.md", "absort/__version__.py"]


logger = Logger()


def bump_file(file: str, new_version: str) -> None:
    substitues = {
        r"__version__\s*=\s*\"(.*)\"": f'__version__ = "{new_version}"',
        r"github.com/MapleCCC/ABSort/compare/.*\.\.\.master": f"github.com/MapleCCC/ABSort/compare/{new_version}...master",
        r"git\+https://github\.com/MapleCCC/ABSort\.git@.*#egg=ABSort": f"git+https://github.com/MapleCCC/ABSort.git@{new_version}#egg=ABSort",
    }

    p = Path(file)
    new_content = p.read_text(encoding="utf-8")

    for pattern, repl in substitues.items():
        new_content, num_of_sub = re.subn(pattern, repl, new_content)
        if not num_of_sub:
            logger.log(
                f"Can't find match of pattern {pattern} in file {file}", file=sys.stderr
            )

    p.write_text(new_content, encoding="utf-8")


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


def retry(
    func: Callable[..., _T],
    total: int = 3,
    backoff_factor: float = 0.1,
    on_except: List[Type[Exception]] = None,
) -> Callable[..., _T]:
    """
    Tips: Pass function arguments by functools.partial.

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

    for i in range(total + 1):
        if i >= 2:
            time.sleep(backoff_factor * (2 ** (i - 1)))
        try:
            return func()
        except exceptions:
            continue

    raise MaxRetryError(f"Reached maximum retries on calling function {func}")


def calculate_new_version(component) -> str:
    old_version_info = semver.VersionInfo.parse(current_version.lstrip("v"))

    method = getattr(old_version_info, f"bump_{component}", None)
    if method is None:
        raise ValueError(
            "Invalid value for argument `component`. "
            "Valid values are `major`, `minor`, `patch`, and `prerelease`."
        )
    new_version_info = method()

    new_version = "v" + str(new_version_info)

    return new_version


def bump_files(new_version: str) -> None:
    for file in FILES_TO_UPDATE:
        logger.log(f"Bump version-related information in {file} ......")
        bump_file(file, new_version)


def preliminary_check() -> None:
    for file in FILES_TO_UPDATE:
        if contains_uncommitted_change(file):
            raise RuntimeError(
                f"{file} contains uncommitted change. "
                "Please clean it up before rerun the script."
            )


@click.command(
    name="bump_version", help="A script to bump version", no_args_is_help=True  # type: ignore
)
@click.argument("component")
@click.option(
    "--no-release", is_flag=True, help="Specify that no GitHub release is published"
)
def main(component: str, no_release: bool) -> None:
    """ A script to bump version """

    logger.log("Conducting preliminary check ...")
    preliminary_check()

    logger.log("Calculating new version......")
    new_version = calculate_new_version(component)

    bump_files(new_version)

    for file in FILES_TO_UPDATE:
        run(["git", "add", file])

    logger.log("Committing the special commit for bumping version......")
    run(["git", "commit", "-m", f"Bump version to {new_version}"])

    logger.log("Creating tag for new version......")
    run(["git", "tag", "-d", new_version])
    run(["git", "tag", new_version])

    # TODO if we change from using subprocess.run to using PyGithub,
    # will the time cost be shorter?
    logger.log("Pushing tag to remote......")
    retry(partial(run, ["git", "push", "origin", new_version]))

    if not no_release:
        logger.log("Creating release in GitHub repo......")

        # TODO when releasing, put in the message about what's updated, what's fixed,
        # and the hash signature of the assets.

        # Create release in GitHub. Upload the zip archive as release asset.
        g = Github(github_account_access_token)
        repo = g.get_repo("MapleCCC/ABSort")
        retry(
            partial(
                repo.create_git_release,
                tag=new_version,
                name=new_version,
                message="For detail changelog, please consult commit history, and commit messages.",
            )
        )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
