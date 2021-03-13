import os

import pytest

from pelutils.logger import Levels, log
from pelutils.tests import MainTest


class TestLogger(MainTest):

    def test_bool_input(self):

        # Default to True
        assert log.bool_input("")
        assert log.bool_input("Yes")
        assert not log.bool_input("No")

        # Default to False
        assert not log.bool_input("", False)
        assert log.bool_input("Yes", False)
        assert not log.bool_input("No", False)

    def test_stdout_stderr(self, capfd: pytest.CaptureFixture):
        test_str = "GME to the moon"
        for level in Levels:
            log(test_str, level=level)
            out, err = capfd.readouterr()
            if level >= Levels.WARNING:
                assert not out and test_str in err
            else:
                assert not err and test_str in out
