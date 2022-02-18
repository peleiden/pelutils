from itertools import permutations, product
from string import ascii_lowercase
import os

import pytest

from pelutils.logging import LogLevels, log
from pelutils.tests import MainTest


class TestLogger(MainTest):

    def setup_class(self):
        super().setup_class()
        self.logfile = os.path.join(self.test_dir, "test_logging.log")
        log.configure(
            self.logfile,
            print_level=LogLevels.DEBUG,
        )

    def test_input(self, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture):
        words = "Lorem ipsum dolor sit amet, consectetur adipiscing elit".split()
        # Generate some test queries and responses
        all_combs = list(permutations(words, 3))
        num_tests = len(all_combs) // 2
        queries = [" ".join(x) for x in all_combs[:num_tests]]
        inputs = [" ".join(x) for x in all_combs[-num_tests:]]
        # Remove log file, so all lines can be predictably read
        os.remove(self.logfile)
        for q, i in zip(queries, inputs):
            monkeypatch.setattr("builtins.input", lambda _: i)
            assert log.input(q) == i
        input_generator = log.input(queries)
        for i in inputs:
            monkeypatch.setattr("builtins.input", lambda _: i)
            assert next(input_generator) == i
        # Test that each query and input has been written twice to the logfile
        with open(self.logfile) as lf:
            for q, i in zip(queries, inputs):
                next(lf)  # This lines declares that the logger is awaiting user input
                assert q in next(lf)
                assert i in next(lf)
            next(lf)
            for q, i in zip(queries, inputs):
                assert q in next(lf)
                assert i in next(lf)

    def test_bool_input(self):
        """ Tests bool input parsing under the eight different cases:
        Nothing/yes-ish/no-ish/gibberish under different possible default values. """
        for default in False, True:
            # Test no input given
            assert log.bool_input("", default=default) == default
            # Test for no-ish input
            for n, o in product("nN", "oO "):
                no = (n + o).strip()
                assert not log.bool_input(no, default=default)
            # Test for yes-ish input
            for y, e, s in product("yY", "eE ", "sS "):
                yes = (y + e + s).strip()
                if e == " " and s != " ":
                    # Unparsable
                    assert log.bool_input(yes, default=default) is None
                else:
                    # Parsable yes-ish
                    assert log.bool_input(yes, default=default)
            # Test that gibberish is always unparsable
            for letter1, letter2 in product(ascii_lowercase[:5], ascii_lowercase[:5]):
                assert log.bool_input(letter1+letter2, default=default) is None

    def test_log_levels(self, capfd: pytest.CaptureFixture):
        test_str = "What LUKE? DaLUKE!"
        for level in LogLevels:
            with log.level(level):
                log.error(test_str)
            with open(self.logfile) as lf:
                lines = lf.readlines()
                last_line = lines[-1] if lines else ""
            out, err = capfd.readouterr()
            if LogLevels.ERROR >= level:
                assert "ERROR" in last_line and test_str in last_line
                assert test_str in out and not err
            else:
                assert not out and not err
        with log.no_log:
            log.section(test_str)
            out, err = capfd.readouterr()
            assert not out and not err
