# ABSort - Sort Function/Class Definitions By Abstraction Level/Layer

<!-- TODO Add GitHub README badges -->

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
```

After ABSorting:

```python
def add_three(x):
    return add_two(increment(x))

def add_two(x):
    return increment(increment(x))

def increment(x):
    return x + 1
```

## Installation

<!-- TODO Specify release version when installing -->

```bash
$ python -m pip install git+https://github.com/MapleCCC/absort.git#egg=absort
```

## Usage

```bash
$ absort <python files>

# Sort all files under current directory and all subdirectories
$ absort .
# This is equivalent to `absort **/*.py`
```

<!-- TODO insert click library `--help` message -->

Alternatively, you can pass Python code from `stdin`.

## Algorithm

Currently a naïve topological sort on the dependency graph, with function/class definitions as graph nodes, and their dependencies as graph edges.

## Limitations

The script is a static analysis tool. It's beyond the tool's capability and scope to handle some heavily dynamic behaviours, e.g. dynamic manipulation of the globals(), locals(), etc.

## License

[MIT](/LICENSE)
