# ABSort - Sort Function/Class Definitions By Abstraction Level/Layer

<!-- TODO add badge about code coverage -->
<!-- TODO add badge about requires.io -->
<!-- TODO add badge about pylint rating -->
[![License](https://img.shields.io/github/license/MapleCCC/absort?color=00BFFF)](LICENSE)
<!-- [![Build Status](https://travis-ci.com/MapleCCC/absort.svg?branch=master)](https://travis-ci.com/MapleCCC/Fund-Info-Fetcher) -->
<!-- [![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/MapleCCC/Fund-Info-Fetcher)](https://github.com/MapleCCC/Fund-Info-Fetcher/releases/latest) -->
[![Semantic release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
[![LOC](https://sloc.xyz/github/MapleCCC/absort)](https://sloc.xyz/github/MapleCCC/absort)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<!-- [![GitHub commits since latest release (by SemVer)](https://img.shields.io/github/commits-since/MapleCCC/absort/latest?sort=semver)](https://github.com/MapleCCC/absort/compare/v1.0.0...master) -->
<!-- TODO which diff method should we use? two dots or three dots? -->

<!-- Add TOC here -->

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

class BigInt:
    pass

print(add_three(BigInt()))
```

After ABSorting:

```python
def add_three(x):
    return add_two(increment(x))

def add_two(x):
    return increment(increment(x))

class BigInt:
    pass

def increment(x):
    return x + 1

print(add_three(BigInt()))
```

## Installation

<!-- TODO Specify release version when installing -->

```bash
$ python -m pip install git+https://github.com/MapleCCC/absort.git#egg=absort
```

## Usage

```bash
$ absort <python files | direcotries>

# Sort all files under current directory and all subdirectories
$ absort .
# This is equivalent to `absort **/*.py`
```

<!-- TODO insert click library `--help` message -->

Alternatively, you can pass Python code from `stdin`.

## Interanl Algorithm

The sorting algorithm is currently a hierarchy level sort on the dependency graph, with function/class definitions as graph nodes, and their dependencies as graph edges.

Hierarchy level sort is a reverse topological sort on the inverted version of the dependency graph.

## Limitations

The script is a static analysis tool. It's beyond the tool's capability and scope to handle some heavily dynamic behaviours, e.g. dynamic manipulation of the globals(), locals(), etc.

## Development

```bash
$ git clone https://github.com/MapleCCC/ABSort.git
$ cd ABSort

# Optionally create a virtual environment for isolation purpose
$ python -m virtualenv .venv
$ source .venv/Scripts/activate

$ python -m pip install -r requirements.txt
$ python -m pip install -r requirements-dev.txt
$ python -m pip install -e .  # Mind the dot
```

## License

[MIT](/LICENSE)
