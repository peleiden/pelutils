from __future__ import annotations
import os
import traceback as tb
from collections import defaultdict
from enum import IntEnum
from functools import update_wrapper
from itertools import chain
from typing import Any, Callable, DefaultDict, Generator, Iterable

from tqdm import tqdm as _tqdm

from pelutils import get_timestamp, get_repo
from .format import RichString


class Levels(IntEnum):
    """ Logging levels by priority. Don't set any to 0, as falsiness is used in the code """
    SECTION  = 6
    CRITICAL = 5
    ERROR    = 4
    WARNING  = 3
    INFO     = 2
    DEBUG    = 1

_STDERR_LEVELS = { Levels.CRITICAL, Levels.ERROR, Levels.WARNING }


# https://rich.readthedocs.io/en/stable/appendix/colors.html
_TIMESTAMP_COLOR = "#72b9e0"
_LEVEL_FORMAT = {
    Levels.SECTION:  "bright_yellow",
    Levels.CRITICAL: "red1",
    Levels.ERROR:    "red3",
    Levels.WARNING:  "gold3",
    Levels.INFO:     "chartreuse3",
    Levels.DEBUG:    "deep_sky_blue1",
}


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

    def with_level(self, level: Levels) -> _LevelManager:
        self.level = level
        return self

    def __enter__(self):
        self.is_active = True

    def __exit__(self, *args):
        self.is_active = False
        del self.level  # Prevent silent failures by having level accidentally set


class _LogErrors:
    """
    Used for catching exceptions with logger and logging them before reraising them
    """

    def __init__(self, log):
        self._log = log

    def __enter__(self):
        pass

    def __exit__(self, et, ev, tb_):
        if et and self._log._collect:
            self._log.log_collected()
        if et:
            self._log._throw(ev, tb_)


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

    _yes = { "j", "y" }
    _no = { "n" }

    @property
    def _logger(self) -> dict:
        return self._loggers[self._selected_logger]
    @property
    def _fpath(self) -> str:
        return self._logger["fpath"]
    @property
    def _default_sep(self) -> str:
        return self._logger["default_sep"]
    @property
    def _include_micros(self) -> bool:
        return self._logger["include_micros"]
    @property
    def _print_level(self) -> Levels:
        return self._logger["print_level"]
    @property
    def _level_mgr(self) -> _LevelManager:
        return self._logger["level_mgr"]
    @property
    def _level(self) -> Levels:
        return self._level_mgr.level

    def __init__(self):
        self._log_errors = _LogErrors(self)
        self._collect = False
        self._collected_log: list[RichString] = list()
        self._collected_print: list[RichString] = list()
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
        print_level       = Levels.INFO,  # Highest level that will be printed. All will be logged. None for no print
    ):
        """ Configure a logger. This must be called before the logger can be used """
        if logger in self._loggers:
            raise LoggingException("Logger '%s' already exists" % logger)
        if self._collect:
            raise LoggingException("Cannot configure a new logger while collecting")
        self._selected_logger = logger
        dirs = os.path.split(fpath)[0]
        if dirs:
            os.makedirs(dirs, exist_ok=True)

        self._loggers[logger]["fpath"] = fpath
        self._loggers[logger]["default_sep"] = default_seperator
        self._loggers[logger]["include_micros"] = include_micros
        self._loggers[logger]["level_mgr"] = _LevelManager()
        self._loggers[logger]["print_level"] = print_level or len(Levels) + 1

        exists = os.path.exists(fpath)
        with open(fpath, "a" if append else "w", encoding="utf-8") as logfile:
            logfile.write("\n\n" if append and exists else "")

        if title:
            self.section(title + "\n")
        if log_commit:
            repo, commit = get_repo()
            if repo is not None:
                self.section(
                    "Executing in repository %s" % repo,
                    "Commit: %s\n" % commit,
                )
            else:
                self.section("Unable to find repository that code was executed in")

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

    def __call__(self, *tolog, with_info=True, sep=None, with_print=None, level: Levels=Levels.INFO):
        self._log(*tolog, level=level, with_info=with_info, sep=sep, with_print=with_print)

    def _write_to_log(self, content: RichString):
        with open(self._fpath, "a", encoding="utf-8") as logfile:
            logfile.write(f"{content}\n")

    @staticmethod
    def _format(s: str, format: str) -> str:
        return f"[{format}]{s}[/]"

    def _log(self, *tolog, level=Levels.INFO, with_info=True, sep=None, with_print=None):
        if not self._loggers:
            return
        if self._level_mgr.is_active and level < self._level_mgr.level:
            return
        sep = sep or self._default_sep
        with_print = level >= self._print_level if with_print is None else with_print
        time = get_timestamp()
        tolog = sep.join([str(x) for x in tolog])
        time_spaces = len(time) * " "
        level_format = level.name + (self._maxlen - len(level.name)) * " "
        space = self._spacing + self._maxlen * " " + self._spacing
        logs = tolog.split("\n")
        rs = RichString(stderr=level in _STDERR_LEVELS)  # Send warning
        if with_info and tolog:
            rs.add_string(
                f"{time}{self._spacing}{level_format}{self._spacing}{logs[0]}".rstrip(),
                (self._format(time, _TIMESTAMP_COLOR) +\
                    self._spacing +\
                    self._format(level_format, _LEVEL_FORMAT[level]) +\
                    self._spacing +\
                    logs[0]).rstrip(),
            )
        else:
            rs.add_string(f"{time_spaces}{space}{logs[0]}".rstrip())
        for i in range(1, len(logs)):
            s = f"\n{time_spaces}{space}{logs[i]}".rstrip()
            rs.add_string(
                s if s.strip() else "\n"
            )
        if not self._collect:
            self._write_to_log(rs)
            if with_print:
                rs.print()
        else:
            self._collected_log.append(rs)
            if with_print:
                self._collected_print.append(rs)

    def _format_tb(self, error: Exception, tb_) -> list[str]:
        stack = list(chain.from_iterable([elem.split("\n") for elem in tb.format_tb(tb_)]))
        stack = [line for line in stack if line.strip()]
        return [
            "ERROR: %s thrown with stacktrace" % type(error).__name__,
            *stack,
            "%s: %s" % (type(error).__name__, error),
        ]

    def _throw(self, error: Exception, tb_=None):
        stack = list()
        has_cause = error.__cause__ is not None
        cur_error = error.__context__
        while cur_error:
            stack += self._format_tb(cur_error, cur_error.__traceback__)
            if has_cause:
                stack += ["", "The above exception was the direct cause of the following exception:", ""]
            else:
                stack += ["", "During handling of the above exception, another exception occurred:", ""]
            has_cause = cur_error.__cause__ is not None
            cur_error = cur_error.__context__
        stack += self._format_tb(error, tb_)
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

    def tqdm(self, iterable: _tqdm) -> Generator:
        """
        Disable printing while iterating over a tqdm object
        Do not use this for for loops that are ended with break statements
        """
        orig_level = self._print_level
        self._logger["print_level"] = len(Levels) + 1
        for elem in iterable:
            yield elem
        self._logger["print_level"] = orig_level

    @classmethod
    def bool_input(cls, inp: str, default=True) -> bool:
        """ Parse a yes/no user input """
        inp = inp.lower()
        if default:
            return inp[0] not in cls._no if inp else True
        else:
            return inp[0] in cls._yes if inp else False

    def _reset_collected(self):
        self._collected_log = list()
        self._collected_print = list()

    def set_collect_mode(self, collect: bool):
        self._collect = collect
        if not collect:
            self._reset_collected()

    def log_collected(self):
        if self._collected_log:
            logs = "\n".join(str(log) for log in self._collected_log)
            self._write_to_log(logs)
        if self._collected_print:
            RichString.multiprint(self._collected_print)

    def clean(self):
        self._loggers = defaultdict(dict)
        self._selected_logger = "default"

    def section(self, *tolog, with_info=True, sep=None, with_print=None, newline=True):
        if newline:
            self._log("")
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.SECTION)

    def critical(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.CRITICAL)

    def error(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.ERROR)

    def warning(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.WARNING)

    def info(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=Levels.INFO)

    def debug(self, *tolog, with_info=True, sep=None, with_print=None):
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
