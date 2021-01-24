from __future__ import annotations
import os
import traceback as tb
from collections import defaultdict
from enum import IntEnum
from functools import update_wrapper
from itertools import chain
from typing import Any, Callable, DefaultDict, Generator, Iterable

from pelutils import get_timestamp, get_repo


class Levels(IntEnum):
    SECTION  = 5
    CRITICAL = 4
    ERROR    = 3
    WARNING  = 2
    INFO     = 1
    DEBUG    = 0


class _LevelManager:
    """
    Used for disabling logging below a certain level
    Example:
    with log.level(Levels.WARNING):
        log.error("This will be logged")
        log.info("This will not be logged")
    """

    level: Levels
    is_active = False

    def __init__(self, level: Levels):
        self.level = level
        self.default_level = level

    def with_level(self, level: Levels) -> _LevelManager:
        self.level = level
        return self

    def __enter__(self):
        self.is_active = True

    def __exit__(self, *args):
        self.is_active = False
        self.level = self.default_level


class _LogErrors:
    """
    Used for catching exceptions with logger and logging them before reraising them
    """

    def __init__(self, log):
        self._log = log

    def __enter__(self):
        pass

    def __exit__(self, et, ev, tb):
        if et is not None:
            self._log.throw(ev, _tb=tb)


class LoggingException(Exception):
    pass


class _Logger:
    """
    A simple logger which creates a log file and pushes strings both to stdout and the log file
    Sections, verbosity and error logging is supported
    """

    _loggers: DefaultDict[str, dict[str, Any]]
    _selected_logger: str
    _maxlen = max(len(l.name) for l in Levels)
    _spacing = 4 * " "

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
    def _level_mgr(self):
        return self._loggers[self._selected_logger]["level_mgr"]
    @property
    def _level(self):
        return self._level_mgr.level

    def __init__(self):
        self._log_errors = _LogErrors(self)
        self._collect = False
        self._collected_log: list[str] = list()
        self._collected_print: list[str] = list()
        self.clean()

    def configure(
        self,
        fpath: str,  # Path to place logger. Any missing directories are created
        title: str,  # Title on first line of logfile
        *,
        default_seperator = "\n",
        include_micros    = False,        # Include microseconds in timestamps
        log_commit        = False,        # Log commit of git repository
        logger            = "default",    # Name of logger
        append            = False,        # Set to True to append to old log file instead of overwriting it
        default_level     = Levels.INFO,  # Default level when using __call__ to log
    ):
        """ Configure a logger. This must be called before the logger can be used """
        if logger in self._loggers:
            raise LoggingException("Logger '%s' already exists" % logger)
        if self._collect:
            raise LoggingException("Cannot configure a new logger while collecting")
        self._selected_logger = logger
        dirs = os.path.join(*os.path.split(fpath)[:-1])
        if dirs:
            os.makedirs(dirs, exist_ok=True)

        self._loggers[logger]["fpath"] = fpath
        self._loggers[logger]["default_sep"] = default_seperator
        self._loggers[logger]["include_micros"] = include_micros
        self._loggers[logger]["level_mgr"] = _LevelManager(default_level)

        exists = os.path.exists(fpath)
        with open(fpath, "a" if append else "w", encoding="utf-8") as logfile:
            logfile.write("\n\n" if append and exists else "")

        if title:
            self.section(title + "\n")
        if log_commit:
            repo, commit = get_repo()
            self.section(
                "Executing in repository %s" % repo,
                "Commit: %s\n" % commit,
            )

    def set_logger(self, logger: str):
        if logger not in self._loggers:
            raise LoggingException("Logger '%s' does not exist" % logger)
        if self._collect:
            raise LoggingException("Cannot configure a new logger while collecting")
        self._selected_logger = logger

    def level(self, level: Levels):
        return self._level_mgr.with_level(level)

    @property
    def log_errors(self):
        return self._log_errors

    def __call__(self, *tolog, with_info=True, sep=None, with_print=True, level: Levels=None):
        self._log(*tolog, level=level, with_info=with_info, sep=sep, with_print=with_print)

    def _write_to_log(self, content: str):
        with open(self._fpath, "a", encoding="utf-8") as logfile:
            logfile.write(content + "\n")

    def _log(self, *tolog, level: Levels=None, with_info=True, sep=None, with_print=True):
        level = level if level is not None else self._level
        if (self._level_mgr.is_active and level < self._level_mgr.level) or not self._loggers:
            return
        sep = sep or self._default_sep
        time = get_timestamp()
        tolog = sep.join([str(x) for x in tolog])
        time_spaces = len(time) * " "
        level_format = level.name + (self._maxlen - len(level.name)) * " "
        space = self._spacing + self._maxlen * " " + self._spacing
        logs = tolog.split("\n")
        if with_info and tolog:
            logs[0] = f"{time}{self._spacing}{level_format}{self._spacing}{logs[0]}"
        else:
            logs[0] = f"{time_spaces}{space}{logs[0]}"
        for i in range(1, len(logs)):
            logs[i] = f"{time_spaces}{space}{logs[i]}"
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

    def _format_tb(self, error: Exception, _tb) -> list[str]:
        stack = tb.format_stack()[:-2] if _tb is None else tb.format_tb(_tb)
        stack = list(chain.from_iterable([elem.split("\n") for elem in stack]))
        stack = [line for line in stack if line.strip()]
        return [
            "ERROR: %s thrown with stacktrace" % type(error).__name__,
            *stack,
            "%s: %s" % (type(error).__name__, error),
        ]

    def throw(self, error: Exception, _tb=None):
        try:
            raise error
        except:
            stack = self._format_tb(error, _tb)
            self.critical(*stack, with_print=False)
        raise error

    def _input(self, prompt: str) -> str:
        self.info("Prompt: '%s'" % prompt, with_print=False)
        response = input(prompt)
        self.info("Input:  '%s'" % response, with_print=False)
        return response

    def input(self, prompt: str | Iterable[str] = "") -> str | Generator[str]:
        """
        Get user input and log both prompt an input
        If prompt is an iterable, a generator of user inputs will be returned
        """
        self._log("Waiting for user input", with_print=False)
        if isinstance(prompt, str):
            return self._input(prompt)
        else:
            return (self._input(p) for p in prompt)

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

    def clean(self):
        self._loggers = defaultdict(dict)
        self._selected_logger = "default"

    def section(self, *tolog, sep=None, with_print=True, newline=True):
        if newline:
            self._log("")
        self._log(*tolog, sep=sep, with_print=with_print, level=Levels.SECTION)

    def critical(self, *tolog, sep=None, with_print=True):
        self._log(*tolog, sep=sep, with_print=with_print, level=Levels.CRITICAL)

    def error(self, *tolog, with_info=True, sep=None, with_print=True):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.ERROR)

    def warning(self, *tolog, with_info=True, sep=None, with_print=True):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.WARNING)

    def info(self, *tolog, with_info=True, sep=None, with_print=True):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.INFO)

    def debug(self, *tolog, with_info=True, sep=None, with_print=True):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.DEBUG)


log = _Logger()


class collect_logs:
    """
    Wrap functions with this class to have them output all their output at once
    Useful with multiprocessing, e.g.
    ```
    with mp.Pool() as p:
        p.map(collect_logs(fun), ...)
    ```
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
