import os
from shutil import rmtree

from . import log, Levels


class MainTest:
    """
    A convenience class that you should inherit from when writing test classes using pytest.
    This class ensures that test path is automatically created and deleted between tests.

    See this example for usage:
    ```
    class SomethingTest(MainTest):
        def test_somefun(self):
            do_something(path=self.test_dir)
            assert "myresultfile.txt" in os.listdir(self.test_dir)
    ```
    """

    # Place temporary test files here
    # Directory will be creating when running test files and removed afterwards
    test_dir = "local_test_files"

    @classmethod
    def setup_class(cls):
        os.makedirs(cls.test_dir, exist_ok = True)
        log.configure(
            os.path.join(cls.test_dir, "tests.log"),
            "Test: %s" % cls.__name__,
            append=True,
            print_level=Levels.DEBUG,
        )

    @classmethod
    def teardown_class(cls):
        log.clean()
        rmtree(cls.test_dir, onerror=cls.ignore_absentee)

    @staticmethod
    def ignore_absentee(_, __, exc_inf):
        except_instance = exc_inf[1]
        if isinstance(except_instance, FileNotFoundError):
            return
        raise except_instance
