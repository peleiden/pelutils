# Repository guidance

## Layout and conventions

- `pelutils/` is a typed Python 3.11+ utility library; `tests/` mirrors its submodules.
  `pelutils/tests/` contains public test helpers, not the project's test suite.
- Public APIs live in submodules and their `__all__` exports. Keep the package root
  limited to `__version__`; preserve API compatibility unless the task requires a change.
- Follow nearby code, add type hints, and use NumPy-style docstrings for public APIs.
  Ruff configuration in `ruff.toml` defines formatting and lint rules.
- Keep docstrings concise; add detail where needed to explain non-obvious behavior or constraints.
- Add regression tests in the corresponding `tests/` directory for behavior changes.
  Update relevant docstrings and optionally `README.md` when changing documented behavior.
- Native code lives in `pelutils/_c/` and builds as `_pelutils_c` through the
  setuptools PEP 517 backend. Use `uv` for project builds and development commands.
  Rebuild after C changes; do not edit or commit compiled artifacts.
- Keep Python tests focused on main use cases, relevant edge cases, and regressions.
  Test C changes more thoroughly, especially boundary conditions and invalid inputs.
- PyTorch is optional at runtime but required by the full test suite. Keep it optional
  when changing library imports or functionality.

## Setup and checks

Run commands from the repository root. Use `uv` for dependency installation, builds,
and invoking development tools; do not use `pip` or invoke project tools outside `uv run`.
Install development dependencies and build the C extension with
`uv sync --python 3.11 --group dev` (requires a compiler and Python headers).
The uv configuration selects the CPU-only PyTorch index. After changing C sources,
rebuild with `uv sync --python 3.11 --group dev --reinstall-package pelutils`.

Run focused tests while iterating, e.g.
`uv run --python 3.11 pytest tests/array/test_unique.py`.
For code changes, use the checks from CI:

```sh
uv run --python 3.11 ruff check pelutils tests
uv run --python 3.11 ruff format --check pelutils tests
uv run --python 3.11 basedpyright pelutils
uv run --python 3.11 pytest tests --cov=pelutils
```

Use `uv run --python 3.11 ruff format` on changed Python files to format them.
For documentation changes, run `uv run --python 3.11 make -C docs html`.
Report checks that failed or could not be run.

The distribution workflow uses cibuildwheel to build wheels and tests the installed
wheel with uv. Its test environment is synced from the locked `dev` group without
installing the source project. Read the Docs also syncs the `dev` group with uv.

Do not check `uv.lock` for updates.
Ignore untracked local files, unless created as part current work.

## Miscellaneous

- Add feature changes to the unreleased section of `CHANGELOG.md`. If none exists, create
  the next version's section, mark it unreleased, and update `pyproject.toml`'s version to match.
  Semantic versioning should be followed.
- Before committing nontrivial changes, request a subagent review. Typo-only and
  formatting-only changes are exempt. If delegation is unavailable, report that limitation.
- Commits fixing specific issues should mention `Resolves #<issue number>` in the commit body.
- Avoid dev lore in docstrings, unless there is a good reason not to.
