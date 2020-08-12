# ABSort - Sort Function/Class Definitions By Abstraction Level/Layer

<!-- TODO Add GitHub README badges -->

## Overview

ABSort is a lightweight library and a command line utility to sort Python function/class definitions by their abstraction levels.

## Installation

```bash
$ python -m pip install git+https://github.com/MapleCCC/absort
```

## Usage

```bash
$ absort <python files>
```

## Limitations

The script is a static analysis tool. It's impossible to handle some heavily dynamic behaviours, e.g. dynamic manipulation of the globals(), locals().

## License

[MIT](/LICENSE)
