---
name: Pelutils Native Changes
description: Use when changing pelutils C sources, native array algorithms, or Python wrappers around _pelutils_c.
---

# Native changes

Paths and commands below are relative to the repository root. Follow `AGENTS.md`.

1. Read the affected sources in `pelutils/_c/`, their Python wrappers, and matching
   tests in `tests/_c/` and `tests/array/`. Check `setup.py` for build configuration.
2. Trace the Python/C interface before editing: pointer ownership and lifetime,
   argument sizes, dtype and layout assumptions, strides, and result buffers.
   Keep Python-side validation and C-side expectations consistent.
3. Preserve documented behavior, including `unique` returning unsorted values.
   Check allocations, cleanup on error paths, bounds, and integer overflow where
   relevant. Keep platform assumptions explicit; do not expand platform support
   unless requested.
4. Add focused regression tests and relevant boundary cases: empty and singleton
   inputs, shapes and axes, supported and rejected dtypes, noncontiguous arrays,
   optional result buffers, and invalid inputs. Exercise only cases relevant to
   the change; compare with NumPy where semantics agree, not output ordering.
5. Rebuild the extension after C changes:

   ```sh
   python -m pip install -e '.[dev]'
   ```

   If rebuilding fails, report the blocker; an old extension does not validate
   new C sources. Do not commit generated binaries.
6. Run the affected tests, then `python -m pytest tests/_c tests/array` for shared
   native changes. Use `pelutils-validate` for final checks and review.

Summarize the interface changes, boundary cases tested, and any remaining risks.
