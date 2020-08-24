#!/usr/bin/env python3

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import click
import semver
from github import Github

sys.path.append(os.getcwd())
from absort.__version__ import __version__ as current_version
from scripts._local_credentials import github_account_access_token


def bump_file(file: str, pattern, repl) -> None:
    p = Path(file)
    old_content = p.read_text(encoding="utf-8")
    new_content = re.sub(pattern, repl, old_content)
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


@click.command()
@click.argument("component")
@click.option("--no-release", is_flag=True, default=False)
def main(component: str, no_release: bool) -> None:
    print("Calculating new version......")

    old_version_info = semver.VersionInfo.parse(current_version)

    method = getattr(old_version_info, f"bump_{component}", None)
    if method is None:
        raise ValueError(
            "Invalid value for argument `component`. "
            "Valid values are `major`, `minor`, `patch`, and `prerelease`."
        )
    new_version_info = method()

    new_version = "v" + str(new_version_info)

    print("Bump the __version__ variable in __version__.py ......")
    bump_file___version__(new_version)

    print("Bump version-related information in README.md ......")
    bump_file_README(new_version)

    run(["git", "add", "absort/__version__.py"])
    # FIXME what if README contains some local changes that we don't
    # want to commit yet?
    run(["git", "add", "README.md"])

    print("Committing the special commit for bumping version......")
    run(["git", "commit", "-m", f"Bump version to {new_version}"])

    print("Creating tag for new version......")
    run(["git", "tag", new_version])

    # TODO if we change from using subprocess.run to using PyGithub,
    # will the time cost be shorter?
    print("Pushing tag to remote......")
    run(["git", "push", "origin", new_version])

    if not no_release:
        print("Creating release in GitHub repo......")

        # TODO when releasing, put in the message about what's updated, what's fixed,
        # and the hash signature of the assets.

        # Create release in GitHub. Upload the zip archive as release asset.
        g = Github(github_account_access_token)
        repo = g.get_repo("MapleCCC/ABSort")
        repo.create_git_release(
            tag=new_version,
            name=new_version,
            message="For detail changelog, please consult commit history, and commit messages.",
        )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
