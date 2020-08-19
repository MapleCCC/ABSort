## High Priority

- How to handle name redefinition.
- Use more advanced AST library, not the naive builtin ast module.
  - astor
  - astunparse
  - libcst
  - astroid

## Medium Priority

- Add docstring to module, function, method, etc. Elaborate on what they really do.
- Deploy poetry.
- Deploy pre-commit.

## Low Priority

- Try README-driven development
- Use semver and conventional commit message guidelines.
- More detail in symbol table.
  - More detail in symbol table to distinguish different variable with same identifier.
- When programming, use Tickey to broadcast keyboard sound.
- Add unit tests
- Release 1.0.0 version
- Check whether ast.iter_child_nodes yield ordered results?

## Uncategorized

- Profile to find performance hotspots. Optimize and accelerate the script.
- Add click parameter help messages.
- Use self-customized ast.get_source_segment implementation to accelerate.
  - Algorithmic optimization
  - Memoirization optimization
  - Rewrite-in-Cython optimization
- Entries from running `rg TODO` across the whole repo.
- Entries from running `rg FIXME` across the whole repo.
- Retain as much original layout as possible to reduce diff size.
- 只 transform contiguous block of declarations 不要动其他部分的源码. This is also beneficial to reducing diff size.
- stackoverflow 关于 Python 测试列表中是否有重复元素的多种 code snippets 写法
- 应用到 isort 的代码中去，再运行一波，看看有没有问题
- 尝试使用 PyPy 来运行，看看会不会加速很大幅度
- 详细看完 Green Tree Sankes 文档，透彻了解
- visit_Name 不同 context 在 Green Tree Snake 文档中查看
- 完善 README
  - 添加 GitHub badges
    - use black code style
    - total line count
    - license
- 在 GitHub 设为 public repo
- Add .isort.cfg
- Add .pylintrc

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
