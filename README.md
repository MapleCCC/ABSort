# ABSort - Sort Python Source Code by Abstraction Levels

<!-- TODO insert profile picture here -->

<!-- TODO add badge about requires.io -->
<!-- TODO add badge about pylint rating -->
<!-- TODO add compatible Python/PyPy versions -->
[![License](https://img.shields.io/github/license/MapleCCC/ABSort?color=00BFFF)](LICENSE)
[![Build Status](https://travis-ci.com/MapleCCC/ABSort.svg?branch=master)](https://travis-ci.com/MapleCCC/ABSort)
[![Test Coverage](https://codecov.io/gh/MapleCCC/ABSort/branch/master/graph/badge.svg)](https://codecov.io/gh/MapleCCC/ABSort)
<!-- [![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/MapleCCC/ABSort)](https://github.com/MapleCCC/ABSort/releases/latest) -->
[![Semantic release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
[![LOC](https://sloc.xyz/github/MapleCCC/ABSort)](https://sloc.xyz/github/MapleCCC/ABSort)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<!-- [![GitHub commits since latest release (by SemVer)](https://img.shields.io/github/commits-since/MapleCCC/ABSort/latest?sort=semver)](https://github.com/MapleCCC/ABSort/compare/v1.0.0...master) -->
<!-- TODO which diff method should we use? two dots or three dots? -->
<!-- TODO add badge about compatible CPython/PyPy versions -->


## Table of Content

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Overview](#overview)
- [Internal Algorithm](#internal-algorithm)
- [Limitations](#limitations)
- [Usage](#usage)
- [Example](#example)
- [Installation](#installation)
- [Development](#development)
  - [Test](#test)
  - [Profile](#profile)
- [Contribution](#contribution)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


## Overview

`isort`, one of the most popular libraries in Python ecosystem, is specialized at sorting import statements. Besides import statements, there are other kinds of statements in Python code that can benefit from a sorting process. What about a tool that sorts function/class definitions? Don't worry, `ABSort` got your back!

`ABSort` is a lightweight library and a command line utility to sort Python source code by their abstraction levels.

<!-- TODO insert demo animation gif here-->
<!-- TODO add "try it on a demo" hyperlink, pointing to a heroku-hosted instance -->


## Internal Algorithm

The default sorting algorithm is a topological sort on the directed acyclic graph formed by strongly connected components of the dependency graph, with function definitions and class definitions as graph nodes, their dependency relations as graph edges.

Another method to realize abstraction level sort is to sort by DFS/BFS order of the dependency graph. This behavior can be opted in with the `--dfs` and `--bfs` CLI options.

For graph nodes within the same abstract level, they are in turn sorted in two options:

1. Quick and naïve: retain original order. This method requires less resources, and results in smaller diff size.

2. Sophisticated: sorted by syntax tree similarity. The syntax tree similarity is calculated by an adoption of the [ZhangShasha algorithm](https://epubs.siam.org/doi/abs/10.1137/0218082). This method is more advanced, and results in better visual outcome.

The sophisticated method is by now the default behavior, unless the CLI option `--no-aggressive` is set.

> Note that the ZhangShasha algorithm is expensive for large trees. To prevent performance regression, when large trees are detected, the faster approximate algorithm [PQ-Gram](https://dl.acm.org/doi/abs/10.1145/1670243.1670247) is used instead.


## Limitations

The script is a static analysis tool. It's beyond the tool's capability and scope to handle some heavily dynamic behaviours, e.g. dynamic manipulation of the `globals()`, `locals()`, etc.


## Usage

```bash
$ absort <python files | direcotries>

# Sort all files under current directory and all subdirectories
$ absort .
# This is equivalent to `absort **/*.py`

$ absort --help
```

```
Usage: absort [OPTIONS] <files or directories to search for Python files>

  A command line utility to sort Python source code by abstraction levels

Options:
  -c, --check                     Check if the file is already well-formatted.
  -d, --diff                      Specify whether to display the diff view
                                  between the original source code and the new
                                  source code.

  -i, --in-place                  Specify whether to modify the file in-place.
                                  This is a dangerous option. Use to your own
                                  risk. A confirmation prompt shows up to give
                                  you second chance to think over.

  --no-fix-main-to-bottom         Specify that the main function doesn't need
                                  to be fixed to the bottom-most. The default
                                  behavior of the program is to fix the main
                                  function to the bottom-most, unless the
                                  `--no-fix-main-to-bottom` option is set.

  -r, --reverse                   Reverse the sort order. The default order is
                                  that the higher the abstraction level the
                                  topper it locates.

  --no-aggressive                 Disable some aggressive transformations to
                                  the source code which are mostly for
                                  cosmetic purpose. Setting this option
                                  retains more original code layout, hence
                                  reducing diff size, if that is desirable.

  -e, --encoding ENCODING         The encoding scheme used to read and write
                                  Python files.  [default: utf-8]

  --comment-strategy COMMENT_STRATEGY
                                  Specify how to treat comments. Possible
                                  values are `push-top`, `attr-follow-decl`,
                                  and `ignore` (not recommended). The default
                                  value is `attr-follow-decl`. `push-top`
                                  specifies that all comments are pushed to
                                  top. `attr-follow-decl` specifies that
                                  comments are treated as attribute of the
                                  following declaration. `ignore` specifies
                                  that comments are ignored and removed.
                                  [default: attr-follow-decl]

  --py PY_VERSION                 Specify the version of Python abstract
                                  grammar being used in parsing input files.
                                  [default: 3.9]

  -q, --quiet                     Suppress all output except the error
                                  channel. To also suppress error channel
                                  please use `2>/dev/null`.

  -v, --verbose                   Increase verboseness.
  --color-off                     Turn off color output. For compatibility
                                  with environment without color code support.

  -y, --yes                       Bypass all confirmation prompts. Dangerous
                                  option. Not recommended.

  --dfs                           Sort in depth-first order.
  --bfs                           Sort in breadth-first order.
  --separate-class-and-function   Specify that class definitions and function
                                  definitions should be separated into
                                  respective sections.

  --version                       Show the version and exit.
  -h, /?, --help                  Show this message and exit.

  While the tool is in the experimental stage, all files are backuped to a
  local cache before processing. If something goes wrong or regret hits you,
  it's always possible to safely recover the original files. The location of
  the backup cache is "~/.absort_cache".
```

Alternatively, you can pass Python code from `stdin`.


## Example

Original code:

```python
def increment(x):
    return x + 1

def add_three(x):
    return add_two(increment(x))

def add_two(x):
    return increment(increment(x))

class Adder:
    method = increment

print(add_three(1))
```

After ABSorting:

```python
def add_three(x):
    return add_two(increment(x))

def add_two(x):
    return increment(increment(x))

class Adder:
    method = increment

def increment(x):
    return x + 1

print(add_three(1))
```


## Installation

Prerequisite: Python>=3.9

You may consider optionally installing [uvloop](https://github.com/magicstack/uvloop) and [orderedsort](https://github.com/simonpercivall/orderedset) to boost speed.

```bash
# Optionally create a virtual environment for isolation purpose
$ python -m virtualenv .venv
$ source .venv/bin/activate

$ python -m pip install git+https://github.com/MapleCCC/ABSort.git@v0.1.0#egg=ABSort
```


## Development

```bash
$ git clone https://github.com/MapleCCC/ABSort.git
$ cd ABSort

# Optionally create a virtual environment for isolation purpose
$ python -m virtualenv .venv
$ source .venv/bin/activate

# Install install prerequisites
$ python -m pip install -r requirements/install.txt
# Install development prerequisites
$ python -m pip install -r requirements/dev.txt

$ python -m pip install -e .  # Mind the dot
```

Alternatively, just a one-liner:

```bash
# Optionally create a virtual environment for isolation purpose
$ python -m virtualenv .venv
$ source .venv/bin/activate

$ python -m pip install -e git+https://github.com/MapleCCC/ABSort.git#egg=ABSort
```


### Test

```bash
# Install test prerequisites
$ python -m pip install -r requirements/test.txt

$ pytest tests
```

<!-- TODO tox -->


### Profile

```bash
$ python -m pip install -U line-profiler

$ python scripts/profile.py
```

Note: special attention needs to be paid to that 1. line-profiler is not able to collect profiling information in non-main threads, and 2. it's most robust practice to have `@profile` be the innermost decorator.


## Contribution

Go to [issues](https://github.com/MapleCCC/ABSort/issues) to send issues or feedbacks.

Pull requests are welcome. It's recommended to make sure test coverage rate is not lower than before.

Some good first issues are:

1. Add more unit tests, especially for those interface not thoroughly covered. Property-based testing is recommended.

2. Fix errors in documents, comments, and type annotations.

3. Refactor existing code to be more concise and readable.


## License

This project is currently licensed under terms of [MIT](LICENSE) license. Feel free to contribute, fork, modify or redistribute.


<!-- Insert content of TODO.md here -->
