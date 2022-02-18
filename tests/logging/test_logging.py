from itertools import chain, permutations, product
from string import ascii_lowercase
import multiprocessing as mp
import os

import pytest

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
        for default in False, True:
            # Test no input given
            assert log.bool_input("", default=default) is default
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

    def test_no_log(self, capfd: pytest.CaptureFixture):
        test_str = "lev med det"
        with log.no_log:
            for level in LogLevels:
                log(test_str, level=level)
                out, err = capfd.readouterr()
                assert not out and not err

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

    def test_collect_with_other_logger(self):
        reps = 1000
        logfile = os.path.join(self.test_dir, "test_logging2.log")
        log = Logger().configure(logfile, print_level=None)
        # Test that logs do not get messed up
        with SimplePool(mp.cpu_count()) as p:
            p.map(_collect_test_fn, reps*[(log, False)])
        with open(logfile) as lf:
            lines = lf.readlines()
        # _collect_test_fn logs out three lines
        assert len(lines) == 3 * reps
        for i, line in enumerate(lines):
            assert "log %i" % (i%3+1) in line

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

        with pytest.raises(LoggingException):
            with log.collect:
                log.configure(logfile)
