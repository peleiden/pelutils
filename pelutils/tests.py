import multiprocessing as mp
import os
import sys
from shutil import rmtree


def restore_argv(fun):
    """
    Decorator function that restores sys.argv after function exits
    This is useful for testing command line argument handling
    ```
    @restore_argv
    def test_my_function():
        sys.argv = ["test", "with", "different", "value", "of", "sys.argv"]
        <tests>
    # sys.argv has value x here
    test_my_function()
    # sys.argv still has value x here
    ```
    """
    def wrapper(*args, **kwargs):
        old_argv = sys.argv.copy()
        try:
            return fun(*args, **kwargs)
        finally:
            sys.argv = old_argv
    return wrapper

class SimplePool:

    """ pytest-cov does not exit properly when using mp.Pool. Using
    this class as a basic drop-in replacement solves it. For details,
    see https://github.com/pytest-dev/pytest-cov/issues/250. """

    def __init__(self, processes=mp.cpu_count()):
        self._processes = processes
        self._pool = None

    def __enter__(self):
        self._pool = mp.Pool(self._processes)
        return self._pool

    def __exit__(self, *_):
        self._pool.close()
        self._pool.join()
        self._pool = None

class UnitTestCollection:
    """ A convenience class for inheriting from when writing test classes using pytest.
    This class ensures that test directory is automatically created and deleted between tests.

    See this example for usage:
    ```py
    class TestMyProgram(UnitTestCollection):
        def test_somefun(self):
            result = ...
            with open(f"{self.test_dir}/myresultfile.txt", "w") as f:
                f.write(result)
            assert "myresultfile.txt" in os.listdir(self.test_dir)
    ``` """

    # Place temporary test files here
    # Directory will be creating when running test files and removed afterwards
    test_dir = ".local_test_files"

    @classmethod
    def setup_class(cls):
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def teardown_class(cls):
        rmtree(cls.test_dir, onerror=cls.ignore_absentee)

    @staticmethod
    def ignore_absentee(_, __, exc_inf):
        except_instance = exc_inf[1]
        if isinstance(except_instance, FileNotFoundError):
            return
        raise except_instance

    @classmethod
    def test_path(cls, path: str) -> str:
        return os.path.join(cls.test_dir, path)
