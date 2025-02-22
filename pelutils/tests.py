from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
from functools import wraps
from shutil import rmtree
from typing import Callable, TypeVar

from pelutils import OS

_C = TypeVar("_C", bound=Callable)

def restore_argv(fun: _C) -> _C:
    """Decorator function to restore sys.argv after function exit.

    This is useful for testing command line argument handling.
    ```py
    @restore_argv
    def test_my_function():
        sys.argv = ["test", "with", "different", "value", "of", "sys.argv"]
        <tests>
    # sys.argv has value x here
    test_my_function()
    # sys.argv still has value x here
    ```
    """  # noqa: D401
    @wraps(fun)
    def wrapper(*args, **kwargs):
        old_argv = sys.argv.copy()
        try:
            return fun(*args, **kwargs)
        finally:
            sys.argv = old_argv
    return wrapper

class SimplePool:
    """Drop-in replacement for mp.Pool for when using it within a pytest context.

    pytest-cov does not exit properly when using mp.Pool. Using this class instead solves it.
    For details, see https://github.com/pytest-dev/pytest-cov/issues/250.
    """

    def __init__(self, processes: int | None = None):
        self._processes = processes or mp.cpu_count()
        self._pool = None

    def __enter__(self):
        self._pool = mp.Pool(self._processes)
        return self._pool

    def __exit__(self, *_):
        self._pool.close()
        self._pool.join()
        self._pool = None

class UnitTestCollection:
    """
    A convenience class for inheriting from when writing test classes using pytest.

    This class ensures that test directory is automatically created and deleted between tests.

    See this example for usage:
    ```py
    class TestMyProgram(UnitTestCollection):
        def test_somefun(self):
            result = ...
            with open(f"{self.test_dir}/myresultfile.txt", "w") as f:
                f.write(result)
            assert "myresultfile.txt" in os.listdir(self.test_dir)
    ```
    """

    test_dir = tempfile.mkdtemp() if OS.is_linux else ".local-test-dir"

    @classmethod
    def setup_class(cls):
        """Create temporary directory for putting test files."""
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def teardown_class(cls):
        """Clean up temporary directory."""
        rmtree(cls.test_dir, onerror=cls.ignore_absentee)

    @staticmethod
    def ignore_absentee(_, __, exc_inf):  # noqa: D102
        except_instance = exc_inf[1]
        if isinstance(except_instance, FileNotFoundError):
            return
        raise except_instance

    @classmethod
    def test_path(cls, path: str) -> str:
        """Return a path inside the test directory.

        `path` would often just be a filename which can be written to and is automatically cleaned up after the test.
        """
        return os.path.join(cls.test_dir, path)
