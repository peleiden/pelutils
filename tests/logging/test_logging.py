import os

import pytest

from pelutils.logging import LogLevels, log
from pelutils.tests import MainTest


class TestLogger(MainTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        log.configure(
            os.path.join(cls.test_dir, "test_logging.log"),
            print_level=LogLevels.DEBUG,
        )

    def test_bool_input(self):
        """ Tests bool input parsing under the eight different cases:
        Nothing/yes-ish/no-ish/gibberish under different possible default values. """

    def test_stdout_stderr(self, capfd: pytest.CaptureFixture):
        test_str = "GME to the moon"
        for level in LogLevels:
            log(test_str, level=level)
            out, err = capfd.readouterr()
            assert test_str in out and not err

    def test_log_levels(self, capfd: pytest.CaptureFixture):
        test_str = "What LUKE? DaLUKE!"
        for level in LogLevels:
            with log.level(level):
                log.error(test_str)
            out, err = capfd.readouterr()
            if LogLevels.ERROR >= level:
                assert test_str in out and not err
            else:
                assert not out and not err
        with log.no_log:
            log.section(test_str)
            out, err = capfd.readouterr()
            assert not out and not err
