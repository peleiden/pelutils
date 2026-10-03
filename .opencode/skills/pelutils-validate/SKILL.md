---
name: Pelutils Change Validation
description: Use to validate pelutils changes before handoff or committing, select checks, and review API, documentation, and version consistency.
---

# Change validation

Paths and commands below are relative to the repository root. Follow `AGENTS.md`.

1. Inspect `git status --short` and the relevant diff, including staged and new
   files. Separate task changes from existing user work; do not revert, format,
   stage, or commit unrelated files.
2. Run focused tests for changed behavior. Keep Python coverage proportionate;
   use `pelutils-native` for C changes and rebuild before testing them.
3. For Python or C code changes, run the repository checks:

   ```sh
   uv run --python 3.11 ruff check pelutils tests
   uv run --python 3.11 ruff format --check pelutils tests
   uv run --python 3.11 basedpyright pelutils
   uv run --python 3.11 pytest tests --cov=pelutils
   ```

   Install/sync dependencies with `uv sync --python 3.11 --group dev` first.
   Format only changed Python files when needed using `uv run --python 3.11 ruff format`.
   For documentation changes, run `uv run --python 3.11 make -C docs html`.
   Guidance-only changes need content and whitespace review, not the code test suite.
   For wheel-build workflow changes, confirm cibuildwheel installs the built wheel
   after syncing the locked `dev` group and runs its tests through uv.
   Read the Docs should install documentation tools by syncing that same uv group.
4. Check public submodule exports, type hints, API compatibility, and optional
   PyTorch behavior where affected. Confirm documentation describes current
   behavior, not development history.
5. For feature changes, verify the unreleased changelog entry and matching
   version follow `AGENTS.md` and semantic versioning. Do not bump the library
   version solely for agent guidance or skills.
6. Before committing nontrivial changes, request an available review subagent.
   Provide the task, changed paths, scope of the diff, and check results; request
   findings by severity with file/line references. Resolve findings and rerun
   affected checks. If delegation is unavailable, report it.

Report changes, checks passed, failures or skipped checks, and unresolved risks.
This skill does not authorize committing, pushing, tagging, or releasing.
