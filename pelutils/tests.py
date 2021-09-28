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
        except:
            raise
        finally:
            sys.argv = old_argv
    return wrapper


class MainTest:
    """
    A convenience class for inheriting from when writing test classes using pytest.
    This class ensures that test path is automatically created and deleted between tests.

    See this example for usage:
    ```
    class SomethingTest(MainTest):
        def test_somefun(self):
            results = ...
            with open("myresultfile.txt", "w") as f:
                f.write(results)
            assert "myresultfile.txt" in os.listdir(self.test_dir)
    ```
    """

    # Place temporary test files here
    # Directory will be creating when running test files and removed afterwards
    test_dir = "local_test_files"

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
