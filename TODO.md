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
