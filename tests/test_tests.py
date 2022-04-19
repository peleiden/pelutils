import sys
from copy import deepcopy

from pelutils.tests import restore_argv, UnitTestCollection


def test_restore_argv():
    initial_argv = deepcopy(sys.argv)

    @restore_argv
    def mock_test():
        sys.argv = ["hello", "there"]
    assert sys.argv == initial_argv
    mock_test()
    assert sys.argv == initial_argv

class TestUnitTestCollection(UnitTestCollection):

    def test_test_path(self):
        testpath = "test"
        testpath = self.test_path(testpath)
        assert testpath.startswith(self.test_dir)
