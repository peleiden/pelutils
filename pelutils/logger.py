import os
import traceback as tb
import copy
from collections import defaultdict
from functools import wraps, update_wrapper
from itertools import chain
from typing import Any, Callable, DefaultDict, Dict, List

from pelutils import get_timestamp


class _Unverbose:
    """
    Used for disabling verbose logging in a code section
    Example:
    with log.unverbose:
        log("This will be logged")
        log.verbose("This will not be logged")
    """
    _allow_verbose = True

    def __enter__(self):
        self._allow_verbose = False

    def __exit__(self, *args):
        self._allow_verbose = True


class _LogErrors:
    """
    Used for catching exceptions with logger and logging them before reraising them
    """

    def __init__(self, log):
        self._log = log

    def __enter__(self):
        pass

    def __exit__(self, et, ev, tb):
        self._log.throw(ev, _tb=tb)


class LoggingException(Exception):
    pass


class _Logger:
    """
    A simple logger which creates a log file and pushes strings both to stdout and the log file
    Sections, verbosity and error logging is supported
    """

    _loggers: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
    _selected_logger = "default"
    _unverbose = _Unverbose()

    @property
    def _fpath(self):
        return self._loggers[self._selected_logger]["fpath"]
    @property
    def _default_sep(self):
        return self._loggers[self._selected_logger]["default_sep"]
    @property
    def _include_micros(self):
        return self._loggers[self._selected_logger]["include_micros"]
    @property
    def _verbose(self):
        return self._loggers[self._selected_logger]["verbose"]

    def __init__(self):
        self._log_errors = _LogErrors(self)
        self._collect = False
        self._collected_log: List[str] = list()
        self._collected_print: List[str] = list()

    def configure(self, fpath: str, title: str, *, default_seperator="\n", include_micros=False, verbose=True, logger="default"):
        """ Configure a logger. This must be called before the logger can be used """
        if logger in self._loggers:
            self.throw(LoggingException("Logger '%s' already exists" % logger))
        if self._collect:
            self.throw(LoggingException("Cannot configure a new logger while collecting"))
        self._selected_logger = logger
        dirs = os.path.join(*os.path.split(fpath)[:-1])
        if dirs:
            os.makedirs(dirs, exist_ok=True)

        self._loggers[logger]["fpath"] = fpath
        self._loggers[logger]["default_sep"] = default_seperator
        self._loggers[logger]["include_micros"] = include_micros
        self._loggers[logger]["verbose"] = verbose

        with open(fpath, "w", encoding="utf-8") as logfile:
            logfile.write("")

        self._log(title + "\n")

    def set_logger(self, logger: str):
        if logger not in self._loggers:
            self.throw(LoggingException("Logger '%s' does not exist" % logger))
        if self._collect:
            self.throw(LoggingException("Cannot configure a new logger while collecting"))
        self._selected_logger = logger

    @property
    def unverbose(self):
        return self._unverbose

    @property
    def log_errors(self):
        return self._log_errors

    def __call__(self, *tolog, with_timestamp=True, sep=None):
        self._log(*tolog, with_timestamp=with_timestamp, sep=sep)

    def _write_to_log(self, content: str):
        with open(self._fpath, "a", encoding="utf-8") as logfile:
            logfile.write(content + "\n")

    def _log(self, *tolog, with_timestamp=True, sep=None, with_print=True):
        sep = sep or self._default_sep
        time = get_timestamp()
        tolog = sep.join([str(x) for x in tolog])
        spaces = len(time) * " "
        space = " " * 5
        logs = tolog.split("\n")
        if with_timestamp and tolog:
            logs[0] = f"{time}{space}{logs[0]}"
        else:
            logs[0] = f"{spaces}{space}{logs[0]}"
        for i in range(1, len(logs)):
            logs[i] = f"{spaces}{space}{logs[i]}"
            if logs[i].strip() == "":
                logs[i] = ""
        tolog = "\n".join(x.rstrip() for x in logs)
        if not self._collect:
            self._write_to_log(tolog)
            if with_print:
                print(tolog)
        else:
            self._collected_log.append(tolog)
            if with_print:
                self._collected_print.append(tolog)

    def verbose(self, *tolog, with_timestamp=True, sep=None, with_print=True):
        if self._verbose and self.unverbose._allow_verbose:
            self._log(*tolog, with_timestamp=with_timestamp, sep=sep, with_print=with_print)

    def section(self, title=""):
        self._log()
        self._log(title)

    def _format_tb(self, error: Exception, _tb):
        stack = tb.format_stack()[:-2] if _tb is None else tb.format_tb(_tb)
        stack = list(chain.from_iterable([elem.split("\n") for elem in stack]))
        stack = [line for line in stack if line.strip()]
        return ["ERROR: %s thrown with stacktrace" % type(error).__name__, *stack]

    def throw(self, error: Exception, _tb=None):
        try:
            raise error
        except:
            stack = self._format_tb(error, _tb)
            self._log(*stack, with_print=False)
        raise error

    def input(self, prompt=""):
        self._log("Waiting for user input")
        self._log("Prompt: %s" % prompt, with_print=False)
        response = input(prompt)
        self._log("Input:  %s" % response, with_print=False)
        return response

    def _reset_collected(self):
        self._collected_log = list()
        self._collected_print = list()

    def set_collect_mode(self, collect: bool):
        self._collect = collect
        if not collect:
            self._reset_collected()

    def log_collected(self):
        if self._collected_log:
            self._write_to_log("\n".join(self._collected_log))
        if self._collected_print:
            print("\n".join(self._collected_print))


log = _Logger()


class collect_logs:
    """
    Wrap functions with this class to have them output all their output at once. Useful with multiprocessing, e.g.
    with mp.Pool() as p:
        p.map(collect_logs(fun), ...)
    Loggers cannot be changed or configured during this
    """
    def __init__(self, fun: Callable):
        self.fun = fun
        update_wrapper(self, fun)

    def __call__(self, *args, **kwargs):
        log.set_collect_mode(True)
        return_value = self.fun(*args, **kwargs)
        log.log_collected()
        log.set_collect_mode(False)
        return return_value
