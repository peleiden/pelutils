import os
import sys
import tempfile
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from shutil import rmtree
from typing import TypeVar

from pelutils import OS

__all__ = ("UnitTestCollection", "restore_argv")

_C = TypeVar("_C", bound=Callable)  # pyright: ignore[reportMissingTypeArgument]


def restore_argv(fun: _C) -> _C:
    """Decorator function to restore sys.argv after function exit.

    This is useful for testing command line argument handling.

    .. code-block:: python

        @restore_argv
        def test_my_function():
            sys.argv = ["test", "with", "different", "value", "of", "sys.argv"]
            # Tests

        # sys.argv has value x here.
        test_my_function()
        # sys.argv still has value x here.
    """  # noqa: D401

    @wraps(fun)
    def wrapper(*args, **kwargs):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        old_argv = sys.argv.copy()
        try:
            return fun(*args, **kwargs)
        finally:
            sys.argv = old_argv

    return wrapper  # pyright: ignore[reportReturnType]


class UnitTestCollection:
    """
    A convenience class for inheriting from when writing test classes using pytest.

    This class ensures that test directory is automatically created and deleted between tests.

    See this example for usage:

    .. code-block:: python

        class TestMyProgram(UnitTestCollection):
            def test_somefun(self):
                result = ...
                with open(f"{self.test_dir}/myresultfile.txt", "w") as f:
                    f.write(result)
                assert "myresultfile.txt" in os.listdir(self.test_dir)
    """

    test_dir = Path(tempfile.mkdtemp() if OS.is_linux else ".local-test-dir").resolve()

    @classmethod
    def setup_class(cls):
        """Create temporary directory for putting test files."""
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def teardown_class(cls):
        """Clean up temporary directory."""
        rmtree(cls.test_dir, onerror=cls.ignore_absentee)

    @staticmethod
    def ignore_absentee(_, __, exc_inf):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
        except_instance = exc_inf[1]
        if isinstance(except_instance, FileNotFoundError):
            return
        raise except_instance

    @classmethod
    def get_test_path(cls, relative_path: str | Path) -> Path:
        """Return a path inside the test directory.

        `path` would often just be a filename which can be written to and is automatically cleaned up after the test.
        """
        return (cls.test_dir / relative_path).resolve()
