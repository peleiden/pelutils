import sys
from copy import deepcopy

from pelutils.tests import restore_argv


def test_restore_argv():
    initial_argv = deepcopy(sys.argv)
    @restore_argv
    def mock_test():
        sys.argv = ["hello", "there"]
    assert sys.argv == initial_argv
    mock_test()
    assert sys.argv == initial_argv
