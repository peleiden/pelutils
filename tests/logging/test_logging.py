import os

import pytest

from pelutils.logging import LogLevels, log
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
        for level in LogLevels:
            log(test_str, level=level)
            out, err = capfd.readouterr()
            if level in _STDERR_LEVELS:
                assert not out and test_str in err
            else:
                assert not err and test_str in out

    def test_log_levels(self, capfd: pytest.CaptureFixture):
        test_str = "What LUKE? DaLUKE!"
        for level in LogLevels:
            with log.level(level):
                log.error(test_str)
            out, err = capfd.readouterr()
            if LogLevels.ERROR >= level:
                assert test_str in out or test_str in err
            else:
                assert not out and not err
        with log.no_log:
            log.section(test_str)
            out, err = capfd.readouterr()
            assert not out and not err
