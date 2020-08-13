# ABSort - Sort Function/Class Definitions By Abstraction Level/Layer

<!-- TODO Add GitHub README badges -->

## Overview

`isort`, one of the top libraries in Python ecosystem, is aimed at sorting import statements. But what about a tool that sorts function/class definitions? Don't worry, `ABSort` got your back!

`ABSort` is a lightweight library and a command line utility to sort Python function/class definitions by their abstraction levels.

## Installation

<!-- TODO Specify release version when installing -->

```bash
$ python -m pip install git+https://github.com/MapleCCC/absort.git#egg=absort
```

## Usage

```bash
$ absort <python files>
```

<!-- TODO insert click library `--help` message -->

## Limitations

The script is a static analysis tool. It's impossible to handle some heavily dynamic behaviours, e.g. dynamic manipulation of the globals(), locals().

## License

[MIT](/LICENSE)
