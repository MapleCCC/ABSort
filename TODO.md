## High Priority

- Use more advanced AST library, not the naive builtin ast module. More high level functionalities to provide.
  - astor
  - astunparse
  - libcst
  - astroid
- Add unit tests
- Release 1.0.0 version
- Deploy pre-commit.
  - Generate README TOC
  - Concatenate TODO.md to README.md
  - Reformat
  - Lint
- Add docstring to module, function, method, etc. Elaborate on what they really do.
- Release 1.0.0rc1 release candidate version.
- Fill in unit tests, then deploy Travis-CI and codecov.io
- 完善 README
- Instead of LRU, maybe we should use LFU?, or frecency? Investigate different cache replacement policy/strategy.
- Pre-commit hook to update absort --help message in README
  - 记得脱敏
- Fill in requirements*.txt files.
- Remove @profile, @add_profile_decorator_to_class_methods decorators.
- Reorder functions in __main__.py by abstraction levels. From higher abstraction level to lower.
- Fill more metadata in setup.py

## Medium Priority

- Deploy poetry.
- stackoverflow 关于 Python 测试列表中是否有重复元素的多种 code snippets 写法
- 应用到 isort 的代码中去，再运行一波，看看有没有问题
- 尝试使用 PyPy 来运行，看看会不会加速很大幅度
- 详细看完 Green Tree Sankes 文档，透彻了解
- visit_Name 不同 context 在 Green Tree Snake 文档中查看
- Remember timestamp to ignore unmodified files
- Use multi-thread/multi-process/asyncIO to accelerate when there are large amounts of input files waiting to be processed.
  - Take inspiration from black tool's source code
  - Take inspiration from autopep8 tool's source code
  - File IO is the most expensive and most suitable for multi-thread.
  - CPU-bound components can be accelerated by multi-processing.
  - IO-bound components can be accelerated by multi-threading or async IO.
- Try to utilize diff-so-fancy when displaying diff.
- Should we use ThreadPoolExecutor or ProcessPoolExecutor? Test which one yields better performance.
- Why does ProcessPoolExecutor perform so much worse than ThreadPoolExecutor? Why?
- 用 line-profiler 测试 absort 项目中多线程 get_dependency_of_decl 是否有助于提升性能，看性能热点占比百分比来定值确定
- Entries from running `rg TODO` across the whole repo.
- Entries from running `rg FIXME` across the whole repo.
- 使用 click 第三方插件来实现 mutually-exclusive options.
- Use click third-party pluggin to realize double confirmation of the -y/--yes option.

## Low Priority

- How to handle name redefinition.
- Try README-driven development
- Use semver and conventional commit message guidelines.
- More detail in symbol table.
  - More detail in symbol table to distinguish different variable with same identifier.
- When programming, use Tickey to broadcast keyboard sound.
- Profile to find performance hotspots. Optimize and accelerate the script.
  - Algorithmic optimization
  - Memoization optimization
  - Rewrite-in-Cython optimization
  - Multi-thread/process optimization
  - Rewrite-in-Generator-Style optimization
  - Caculate and Save for next time optimization
- Provide a programmatical interface.
- Can we just use tokenize.detect_encoding to replace autopep8.detect_encoding?
- Use click's mechanism to specify that two options are mutually exclusive.
- Stress test against CPython site-packages, see if any bugs are spotted.
- What's the elegant way to pass bunch of cli parameters around functions?
  - Take inspiration from black tool's source code.
  - Take inspiration from autopep8 tool's source code.
  - It might be a good idea and elegant way to use global object to pass command line arguments around.

## Uncategorized

## Changelog

- Rename `_env_list` to `_symtab_stack`.
- Rename `GetDependencyVisitor` to `GetUndefinedVariableVisitor`.
- Consider global and nonlocal.
- Remove unused imports.
- Copy Graph.py from Source-Concater reposiroty.
- Reserve comments and blank lines and whitespace layouts. They are important part of the code style.
  - Reserve top level comments
- Handle comments. We don't want to lose comments after absort processing a file.
- Add LICENSE
- Add setup.py
- 去除 reformat code
- visit_ClassDef visit keywords attribute
- topological sort 的时候去除无关的 graph node，这里很容易导致之后维护的时候出错
- decl_ids 改成 decl_names
- 添加 cli option --comment-is-attribute-of-following-declaration
- add confirmation prompt to the dangerous options, eg. --in-place.
- Add .isort.cfg
- As a command line tool that deals with files, we should proceed on failure. Not fail fast and early.
- Use self-customized ast.get_source_segment implementation to accelerate.
  - Algorithmic optimization
  - Memoization optimization
  - Rewrite-in-Cython optimization
  - Multi-thread/process optimization
- Remove hierarchy level sort related.
- It's syntactically correct to have two functions depending on each other. Circle in dependency graph should not be error.
- Fix the bug of starnge result after absorting isort.main module.
- 只 transform contiguous block of declarations 不要动其他部分的源码. This is also beneficial to reducing diff size, and optimize performance.
- Fix the bug: Adding heurstic blank lines at the front should be only applicable to declarations.
- Collect statistics of failure cases. And print summary digest at the end of execution to show user.
- Extract absort_files
- Remove more-itertools dependency
- Some error related information should be printed to stderr, not stdout.
- Add click parameter help messages.
- Use intelligent detect file encoding, instead of hardcoding UTF-8. Take inspiration from the autopep8 cli tool.
- 在 GitHub 设为 public repo
- Retain as much original layout as possible to reduce diff size.
- Add .pylintrc
- Specify release version when installing, in README.
- Open issue in https://github.com/python/typeshed about NodeTransformer.generic_visit method's return t
- Check whether ast.iter_child_nodes yield ordered results?
  - ANSWER: judging from source code, it does yield ordered results.
- 完善 README
  - 添加 GitHub badges
    - use black code style
    - total line count
    - license
  - add examples to showcase
- Read about Python namespace and scope topics, read them crystal clear, then modify visitors.py.
  - Sample read: https://realpython.com/python-namespaces-scope/
- Critical bugs: visitors.py implementation is severely buggy.
- The whole implementation in visitors.py is a mess and catastrophic! We need REWRITE IT!!!
  - Read Pylint source code to figure out how to properly detect undefined variables.
- Rewrite, refactor main function. The body code of main function is right now a bunch of mess. Go beyond executor.map/submit. There are more freedom in interface to use. Examine the async/await keyword, Future, Promise, etc.
  - Take inspiration from black tool's source code.
- GetUndefinedVariableVisitor __slots__ doesn't seem to work?
  - ANSWER: from doc: "When inheriting from a class without __slots__, the __dict__ and __weakref__ attribute of the instances will always be accessible.". Reference: https://docs.python.org/3/reference/datamodel.html#object.__slots__
- Fix race condition on writing to stdout/stderr in absort_files()
- Try to use threading.lock or asyncio.lock to solve race condition on writing to stdout/stderr.
- Refactor absort_files(). Break larget function into multiple small functions.


## TIL

- Path.name is different from Path.__str__()
  - Path.name is "A string representing the final path component, excluding the drive and root, if any"
  - Path.__str__ is "The string representation of a path is the raw filesystem path itself (in native form, e.g. with backslashes under Windows), which you can pass to any function taking a file path as a string"
