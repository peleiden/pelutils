from itertools import chain, permutations, product
from string import ascii_lowercase
import multiprocessing as mp
import os
import re

import pytest
from pelutils import UnsupportedOS, OS

from pelutils.logging import LogLevels, Logger, log, LoggingException
from pelutils.tests import UnitTestCollection, SimplePool


def _collect_test_fn(args):
    logger, do_fail = args
    with logger.collect:
        logger("log 1 from %s" % mp.current_process()._identity)
        logger("log 2 from %s" % mp.current_process()._identity)
        if do_fail:
            raise RuntimeError
        logger("log 3 from %s" % mp.current_process()._identity)

class TestLogger(UnitTestCollection):

    def setup_class(self):
        super().setup_class()
        self.logfile = os.path.join(self.test_dir, "test_logging.log")
        log.configure(
            self.logfile,
            print_level=LogLevels.DEBUG,
        )

    def get_last_line(self) -> str:
        with open(self.logfile) as fh:
            return next(line for line in fh.readlines()[::-1] if line.strip())

    def test_input(self, monkeypatch: pytest.MonkeyPatch):
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
        for default in False, True, None:
            # Test no input given
            assert log.parse_bool_input("", default=default) is default
            # Test for no-ish input
            for n, o in product("nN", "oO "):
                no = (n + o).strip()
                assert not log.parse_bool_input(no, default=default)
            # Test for yes-ish input
            for y, e, s in product("yY", "eE ", "sS "):
                yes = (y + e + s).strip()
                if e == " " and s != " ":
                    # Unparsable
                    assert log.parse_bool_input(yes, default=default) is None
                else:
                    # Parsable yes-ish
                    assert log.parse_bool_input(yes, default=default)

            # Test that gibberish is always unparsable
            for letter1, letter2 in product(ascii_lowercase[:5], ascii_lowercase[:5]):
                assert log.parse_bool_input(letter1+letter2, default=default) is None

    def test_parse_user_bool_input(self, monkeypatch: pytest.MonkeyPatch):
        """ Tests input and bool parsing in combination. """
        for final_answer in "ny":
            inputs = iter(("unparsable", "gibberish", final_answer))
            user_input = None
            while user_input is None:
                monkeypatch.setattr("builtins.input", lambda _: next(inputs))
                user_input = log.parse_bool_input(log.input("Is the weather nice today? "))
            assert user_input == (True if final_answer == "y" else False)

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

    def test_no_log(self, capfd: pytest.CaptureFixture):
        test_str = "lev med det"
        with log.no_log:
            for level in LogLevels:
                log(test_str, level=level)
                out, err = capfd.readouterr()
                assert not out and not err

    def test_level_methods(self, capfd: pytest.CaptureFixture):
        methods = log.debug, log.info, log.warning, log.error, log.critical, log.section
        for method, level in zip(methods, sorted(LogLevels)):
            method("Bulbasaur is underrated")
            stdout, _ = capfd.readouterr()
            assert level.name in stdout

    def test_log_commit(self, capfd: pytest.CaptureFixture):
        """ Tests are assumed to be run from within the
        pelutils git repository root or above. If not, this test will fail. """
        log.log_repo()
        stdout, _ = capfd.readouterr()
        if ".git" in os.listdir("."):
            assert re.search(r"\b[0-9a-f]{40}\b", stdout)
        else:
            assert re.search(r"\b[0-9a-f]{40}\b", stdout) is None

    @pytest.mark.skipif(OS.is_windows, reason="Log collection is not supported on Windows")
    def test_collect(self):
        reps = 1000
        # Clear log file
        os.remove(self.logfile)
        # Test that logs do not get messed up
        with SimplePool(mp.cpu_count()) as p:
            p.map(_collect_test_fn, reps*[(log, False)])
        with open(self.logfile) as lf:
            lines = lf.readlines()
        # _collect_test_fn logs out three lines
        assert len(lines) == 3 * reps
        for i, line in enumerate(lines):
            assert "log %i" % (i%3+1) in line

    @pytest.mark.skipif(OS.is_windows, reason="Log collection is not supported on Windows")
    def test_collect_with_errors(self):
        reps = 1000
        # Clear log file
        os.remove(self.logfile)
        # Test that logs do not get messed up
        with SimplePool(mp.cpu_count()) as p:
            args = reps*[(log, False)]
            args[reps//2] = (log, True)
            with pytest.raises(RuntimeError):
                p.map(_collect_test_fn, args)
        with open(self.logfile) as lf:
            lines = lf.readlines()
        # _collect_test_fn logs out three lines but one function has a log less
        assert 0 < len(lines) < 3 * reps
        for prevline, newline in zip(lines[:-1], lines[1:]):
            if "log 1" in newline:
                assert "log 2" in prevline or "log 3" in prevline
            elif "log 2" in newline:
                assert "log 1" in prevline
            elif "log 3" in newline:
                assert "log 2" in prevline
            else:
                raise RuntimeError("'log i' not found in '%s'" % repr(newline))

    @pytest.mark.skipif(OS.is_windows, reason="Log collection is not supported on Windows")
    def test_collect_with_other_logger(self):
        reps = 1000
        logfile = os.path.join(self.test_dir, "test_logging2.log")
        log = Logger().configure(logfile, print_level=None)
        # Test that logs do not get messed up
        with SimplePool() as p:
            p.map(_collect_test_fn, reps*[(log, False)])
        with open(logfile) as lf:
            lines = lf.readlines()
        # _collect_test_fn logs out three lines
        assert len(lines) == 3 * reps
        for i, line in enumerate(lines):
            assert "log %i" % (i%3+1) in line

    @pytest.mark.skipif(not OS.is_windows, reason="Error should only be raised on Windows")
    def test_collect_error_on_windows(self):
        reps = 100
        with pytest.raises(UnsupportedOS), SimplePool() as p:
            p.map(_collect_test_fn, reps*[(log, False)])

    def test_multiple_loggers(self, capfd: pytest.CaptureFixture):
        os.remove(self.logfile)
        logfile2 = os.path.join(self.test_dir, "test_logging2.log")
        log2 = Logger().configure(logfile2, print_level=None)
        logs = [
            ("logger",),
            ("logger", "bogger"),
            ("logger", "bogger", "hogger")
        ]
        for tolog in logs:
            log(*tolog)
            stdout, _ = capfd.readouterr()
            assert all(x in stdout for x in tolog)
            log2(*tolog)
            stdout, _ = capfd.readouterr()
            assert not stdout
        with open(self.logfile) as lf, open(logfile2) as lf2:
            logger_iter = chain(*logs)
            for line1, line2 in zip(lf, lf2):
                log_item = next(logger_iter)
                assert log_item in line1 and log_item in line2

    def test_reconfiguration(self):
        log = Logger()
        logfile = os.path.join(self.test_dir, "test_logging2.log")
        with pytest.raises(LoggingException):
            log("This fails")

        log.configure(logfile)
        log("This does", "not fail")
        with open(logfile) as lf:
            lines = lf.readlines()
        assert "This does" in lines[0]
        assert "not fail" in lines[1]

        log.configure(logfile, default_seperator=" ", append=True)
        log("This does", "not fail")
        with open(logfile) as lf:
            lines = lf.readlines()
        assert "This does not fail" in lines[2]

        with pytest.raises(UnsupportedOS if OS.is_windows else LoggingException):
            with log.collect:
                log.configure(logfile)

    def test_log_error(self):
        # Log some random stuff to make sure previous tests do not interfere
        log("Hello there")

        # First, test that errors are caught only when within log.log_errors context
        with pytest.raises(ZeroDivisionError):
            0 / 0
        assert ZeroDivisionError.__name__ not in self.get_last_line()

        with pytest.raises(ZeroDivisionError):
            with log.log_errors:
                0 / 0
        assert ZeroDivisionError.__name__ in self.get_last_line()

        # Then test that it also works with SystemExit when the exit code is zero
        with pytest.raises(SystemExit):
            with log.log_errors:
                raise SystemExit(0)
        assert SystemExit.__name__ not in self.get_last_line()

        with pytest.raises(SystemExit):
            with log.log_errors:
                raise SystemExit(1)
        assert SystemExit.__name__ in self.get_last_line()

    def test_whitespace(self, capfd: pytest.CaptureFixture):
        string = "dQw4w9WgXcQ"
        printed_lines = list()
        logged_lines = list()

        log(string, string)
        stdout, _ = capfd.readouterr()

        printed_lines += (x for x in stdout.split("\n") if x)

        with open(self.logfile) as fh:
            lines = fh.readlines()
            logged_lines += lines[-2:]

        log(string, string, with_info=False)
        stdout, _ = capfd.readouterr()

        printed_lines += (x for x in stdout.split("\n") if x)

        with open(self.logfile) as fh:
            lines = fh.readlines()
            logged_lines += lines[-2:]

        for i in range(3):
            assert printed_lines[i].index(string) == \
                   printed_lines[i+1].index(string) == \
                   logged_lines[i].index(string) == \
                   logged_lines[i+1].index(string)
