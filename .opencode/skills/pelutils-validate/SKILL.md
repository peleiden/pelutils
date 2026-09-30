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
   ruff check pelutils tests
   ruff format --check pelutils tests
   basedpyright pelutils
   python -m pytest tests --cov=pelutils
   ```

   Format only changed Python files when needed. For documentation changes,
   run `make -C docs html`. Guidance-only changes need content and whitespace
   review, not the code test suite.
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
