# ABSort - Sort Function/Class Definitions By Abstraction Level/Layer

<!-- TODO add badge about code coverage -->
<!-- TODO add badge about requires.io -->
<!-- TODO add badge about pylint rating -->
[![License](https://img.shields.io/github/license/MapleCCC/ABSort?color=00BFFF)](LICENSE)
<!-- [![Build Status](https://travis-ci.com/MapleCCC/ABSort.svg?branch=master)](https://travis-ci.com/MapleCCC/Fund-Info-Fetcher) -->
<!-- [![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/MapleCCC/Fund-Info-Fetcher)](https://github.com/MapleCCC/Fund-Info-Fetcher/releases/latest) -->
[![Semantic release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
[![LOC](https://sloc.xyz/github/MapleCCC/ABSort)](https://sloc.xyz/github/MapleCCC/ABSort)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<!-- [![GitHub commits since latest release (by SemVer)](https://img.shields.io/github/commits-since/MapleCCC/ABSort/latest?sort=semver)](https://github.com/MapleCCC/ABSort/compare/v1.0.0...master) -->
<!-- TODO which diff method should we use? two dots or three dots? -->

## TOC

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Overview](#overview)
- [Example](#example)
- [Installation](#installation)
- [Usage](#usage)
- [Interanl Algorithm](#interanl-algorithm)
- [Limitations](#limitations)
- [Development](#development)
  - [Test](#test)
  - [Profile](#profile)
- [Contribution](#contribution)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Overview

`isort`, one of the most popular libraries in Python ecosystem, is specialized at sorting import statements. Besides import statements, there are other kinds of statements in Python code that can benefit from a sorting process. What about a tool that sorts function/class definitions? Don't worry, `ABSort` got your back!

`ABSort` is a lightweight library and a command line utility to sort Python function/class definitions by their abstraction levels.

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

```bash
# Optionally create a virtual environment for isolation purpose
$ python -m virtualenv .venv
$ source .venv/Scripts/activate

$ python -m pip install git+https://github.com/MapleCCC/ABSort.git@v0.1.0#egg=ABSort
```

## Usage

```bash
$ absort <python files | direcotries>

# Sort all files under current directory and all subdirectories
$ absort .
# This is equivalent to `absort **/*.py`

$ absort --help
"""
Usage: absort [OPTIONS] <files or directories to search for Python files>

  A command line utility to sort function/class definitions by abstraction
  levels

Options:
  -d, --diff                      Specify whether to display diff view between
                                  original source code and processed source
                                  code.

  -i, --in-place                  Specify whether to modify file in-place.
                                  This is a dangerous option. Use to your own
                                  risk. A confirmation prompt shows up to give
                                  you second chance to think over.

  --no-fix-main-to-bottom         Specify that main function doesn't need to
                                  be fixed to the bottom-most. The default
                                  behavior of the program is to fix the main
                                  function to the bottom-most, unless the
                                  `--no-fix-main-to-bottom` option is set.

  -r, --reverse                   Reverse the sort order. The default order is
                                  that the higher the abstraction level the
                                  topper it locates.

  -a, --aggressive                Enable some aggressive transformations to
                                  the source code, mostly for cosmetic
                                  purpose.

  -e, --encoding TEXT             The encoding scheme used to read and write
                                  Python files.  [default: utf-8]

  -c, --comment-strategy COMMENT_STRATEGY
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

  -q, --quiet                     Suppress all output except the error
                                  channel.

  -v, --verbose                   Increase verboseness.
  --version                       Show the version and exit.
  --help                          Show this message and exit.
"""
```

Alternatively, you can pass Python code from `stdin`.

## Interanl Algorithm

The sorting algorithm is currently a reversed topological sort on the dependency graph, with function/class definitions as graph nodes, and their dependency relations as graph edges.

## Limitations

The script is a static analysis tool. It's beyond the tool's capability and scope to handle some heavily dynamic behaviours, e.g. dynamic manipulation of the globals(), locals(), etc.

## Development

```bash
$ git clone https://github.com/MapleCCC/ABSort.git
$ cd ABSort

# Optionally create a virtual environment for isolation purpose
$ python -m virtualenv .venv
$ source .venv/Scripts/activate

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
$ source .venv/Scripts/activate

$ python -m pip install -e git+https://github.com/MapleCCC/ABSort.git#egg=ABSort
```

### Test

```bash
# Install test prerequisites
$ python -m pip install -r requirements/test.txt

$ pytest tests
```

<!-- tox -->

### Profile

```bash
$ python -m pip install -U line-profiler

$ python scripts/profile.py
```

Note: special attention needs to be paid to that 1. line-profiler is not able to collect profiling information in non-main threads, and 2. it's most robust practice to have `@profile` be the innermost decorator.

## Contribution

Go to [issues](https://github.com/MapleCCC/ABSort/issues) to send issues or feedbacks. Pull requests are welcome.

## License

This project is currently licensed under terms of [MIT](LICENSE) license. Feel free to contribute, fork, modify or redistribute.
