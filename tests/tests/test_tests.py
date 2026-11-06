import sys
from copy import deepcopy

import pytest

from pelutils.tests import UnitTestCollection, restore_argv


def test_restore_argv():
    initial_argv = deepcopy(sys.argv)

    @restore_argv
    def mock_test():
        sys.argv = ["hello", "there"]

    assert sys.argv == initial_argv
    mock_test()
    assert sys.argv == initial_argv


def test_restore_argv_on_exception():
    initial_argv = deepcopy(sys.argv)

    @restore_argv
    def failing_test():
        sys.argv = ["hello", "there"]
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        failing_test()
    assert sys.argv == initial_argv


def test_restore_argv_passes_through():
    @restore_argv
    def add(a: int, *, b: int) -> int:
        sys.argv.append("extra")
        return a + b

    initial_argv = deepcopy(sys.argv)
    assert add(1, b=2) == 3
    assert add.__name__ == "add"
    assert sys.argv == initial_argv


class TestUnitTestCollection(UnitTestCollection):
    def test_test_path(self):
        testpath = self.get_test_path("test")
        assert testpath.is_relative_to(self.test_dir.resolve())
