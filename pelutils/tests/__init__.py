"""Small helpers for writing tests that touch the filesystem or global state.

Tests that write files or mutate ``sys.argv`` come with the same boilerplate every time:
create a scratch directory and remember to delete it afterwards, or snapshot a global and
restore it so the next test is not affected. Forgetting either leaves stray files on disk
or leaks state between tests, causing failures that are painful to track down. This module
provides two focused helpers that take care of that bookkeeping for you:
:class:`UnitTestCollection`, a pytest base class that creates a temporary directory before
a test class runs and removes it afterwards, and :func:`restore_argv`, a decorator that
restores ``sys.argv`` after the wrapped function returns.

Quick start
-----------

.. code-block:: python

    from pelutils.tests import UnitTestCollection

    class TestMyProgram(UnitTestCollection):
        def test_writes_output(self):
            path = self.get_test_path("result.txt")   # inside the managed temp dir
            path.write_text("hello")
            assert path.exists()
        # The temporary directory is created and cleaned up automatically.

See :class:`UnitTestCollection` for the managed ``test_dir`` and :meth:`get_test_path`, and
:func:`restore_argv` for isolating command-line-argument handling in a single test.
"""

from ._tests import UnitTestCollection, restore_argv

__all__ = ("UnitTestCollection", "restore_argv")
