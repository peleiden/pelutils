from __future__ import annotations

import os
import traceback as tb
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Optional

from pelutils import OS, UnsupportedOS, get_repo, get_timestamp
from pelutils.format import RichString

from ._rotate import _LogFileRotater
from ._utils import LogLevels, _CollectLogs, _LevelManager, _LogErrors

# https://rich.readthedocs.io/en/stable/appendix/colors.html
TIMESTAMP_COLOR = "#72b9e0"
LEVEL_FORMAT = {
    LogLevels.SECTION:  "bright_yellow",
    LogLevels.CRITICAL: "red1",
    LogLevels.ERROR:    "red3",
    LogLevels.WARNING:  "gold3",
    LogLevels.INFO:     "chartreuse3",
    LogLevels.DEBUG:    "deep_sky_blue1",
}

class LoggingException(RuntimeError):
    """Raised on logging-related errors."""

class Logger:
    """A simple logger which creates a log file and pushes strings both to stdout and the log file. See .configure for usage details.

    Main features include automatically logging errors and their stacktrace (see _Logger.log_errors),
    collecting logs for multiprocessing (see _Logger.collect), and colourful prints.
    """

    _selected_logger: str
    _maxlen = max(len(level.name) for level in LogLevels)
    _spacing = 4 * " "

    _yes = "yes"
    _no = "no"

    def __init__(self):
        self._log_errors = _LogErrors(self)
        self._is_configured = False
        self._collect = False
        self._collected_log: list[RichString] = list()
        self._collected_print: list[RichString] = list()
        self._level_mgr = _LevelManager()
        self._log_errors = _LogErrors(self)

    def configure(
        self,
        fpath: str | Path | None, *,
        default_seperator: str  = "\n",
        append: bool = False,
        print_level: LogLevels | None = LogLevels.INFO,
        rotation: str | None = None,
    ):
        r"""Configure a logfile. This method must be called before a Logger can be used.

        A Logger can be reconfigured at any time, so long as it is not collecting.

        Parameters
        ----------
        fpath : str | Path | None
            Path to logfile. Missing directories are created. If None, no file is created, and the logger works more like an advaned `print`.
        default_seperator : str, optional
            Default seperator when logging multiple strings in a single call, by default \n.
        append : bool, optional
            If True, existing log file(s) are appended to rather that overwritten, by default False.
        print_level : LogLevels | None, optional
            Highest level that will be printed. If None, nothing will be printed, by default LogLevels.INFO.
        rotation : str | None, optional
            Command specifying when to rotate the log file, e.g. "day" or "1 GB" or None for no rotation, by default None.

        Returns
        -------
        Logger
            self is returned to allow for chaining when creating a Logger instance (`log = Logger().configure(...)`).
        """
        if self._collect:
            raise LoggingException("Logger cannot be reconfigured while collecting")

        # Create logfile
        if fpath is not None:
            self._rotater = _LogFileRotater(rotation, Path(fpath))
            self._rotater.base_file.parent.mkdir(parents=True, exist_ok=True)
            # Create file if it doesn't exist
            with self._rotater.resolve_logfile(0).open("a" if append else "w", encoding="utf-8"):
                pass
        else:
            self._rotater = None

        self._default_sep = default_seperator
        self._print_level = print_level if print_level is not None else max(LogLevels) + 1
        self._is_configured = True

        return self

    def level(self, level: LogLevels):
        """Log only at given level and above. Use with a with block."""
        return self._level_mgr.with_level(level)

    @property
    def no_log(self):
        """Disable logging inside a with block."""
        return self._level_mgr.with_level(max(LogLevels)+1)

    @property
    def log_errors(self):
        """Use in a `with` block. Any errors thrown within the block are logged with the full stacktrace."""
        return self._log_errors

    def _write_to_log(self, content: RichString):
        if self._rotater is not None:
            content = f"{content}\n".encode()
            with self._rotater.resolve_logfile(len(content)).open("ab") as f:
                f.write(content)

    @staticmethod
    def _format(s: str, format: str) -> str:
        return f"[{format}]{s}[/]"

    def _log(
        self,
        *tolog: str,
        level=LogLevels.INFO,
        with_info: bool = True,
        sep: str | None = None,
        with_print: bool | None = None,
    ):
        """Log given strings.

        Parameters
        ----------
        level : LogLevels, optional
            Level (or severity) at which to log, by default LogLevels.INFO.
        with_info : bool, optional
            Include timestamp and severity information, by default True.
        sep : str | None, optional
            String seperator. If None, use default_separator from .configure is used, by default None.
        with_print : bool | None, optional
            If given, force enable/disable printing, otherwise determined by the log level, by default None.
        """
        if not self._is_configured:
            raise LoggingException("Logger has not been configured. Create a new logger with log = Logger().configure(...)")
        if self._level_mgr.level is not None and level < self._level_mgr.level:
            return
        sep = sep or self._default_sep
        with_print = level >= self._print_level if with_print is None else with_print
        time = get_timestamp()
        tolog = sep.join([str(x) for x in tolog])
        time_spaces = len(time) * " "
        level_format = level.name + (self._maxlen - len(level.name)) * " "
        space = self._spacing + self._maxlen * " " + self._spacing + " "
        logs = tolog.split("\n")
        rs = RichString()
        if with_info and tolog:
            rs.add_string(
                f"{time}{self._spacing}{level_format}{self._spacing} ",
                self._format(time, TIMESTAMP_COLOR) + \
                    self._spacing + \
                    self._format(level_format, LEVEL_FORMAT[level]) + \
                    self._spacing + " ",
            )
            rs.add_string(logs[0].rstrip())
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

    def log_with_stacktrace(self, error: Exception, level=LogLevels.ERROR, with_print=False):
        """Log an exception along with the full stacktrace."""
        self._log(
            f"{type(error)} was thrown with the following stacktrace:",
            tb.format_exc(),
            level=level,
            sep="\n",
            with_print=with_print,
        )

    def _input(self, prompt: str) -> str:
        self.info(f"Prompt: \"{prompt}\"", with_print=False)
        response = input(prompt)
        self.info(f"Input:  \"{response}\"", with_print=False)
        return response

    def input(self, prompt: str | Iterable[str] = "") -> str | Generator[str]:
        """Get user input and log both prompt an input.

        If prompt is an iterable, a generator of user inputs will be returned.
        """
        self._log("Waiting for user input", with_print=False)
        if isinstance(prompt, str):
            return self._input(prompt)
        else:
            return (self._input(p) for p in prompt)

    @classmethod
    def parse_bool_input(cls, answer: str, *, default: bool | None = None) -> bool | None:
        """Validate user yes/no input. None is returned if the input is not parsable.

        Example:
        ```
        answer = log.input("Do you like this question? [y/N] ")
        likes_answer = log.bool_input(answer, default=False)
        # User answered y/Y/yes/Yes/YES/yE etc.
        likes_answer == True
        # User answered nothing or n/N/no/No/nO/NO
        likes_answer == False
        # User answered something unparsable as yes/no
        likes_answer == None
        ```
        """
        answer = answer.strip()
        if not answer:
            return default
        if cls._yes.startswith(answer.lower()):
            return True
        if cls._no.startswith(answer.lower()):
            return False

    def log_repo(self, level=LogLevels.DEBUG):
        """Niceness method for logging the git repo that the code is run in."""
        repo, commit = get_repo()
        if repo is not None:
            self._log(
                f"Executing in repository: {repo}",
                f"Commit: {commit}",
                level=level,
            )
        else:
            self.debug("Unable to find repository that code was executed in")

    def _reset_collected(self):
        self._collected_log = list()
        self._collected_print = list()

    def _set_collect_mode(self, collect: bool):
        self._collect = collect
        if not collect:
            self._reset_collected()

    def _log_collected(self):
        if self._collected_log:
            logs = os.linesep.join(str(log) for log in self._collected_log)
            self._write_to_log(logs)
        if self._collected_print:
            RichString.multiprint(self._collected_print)

    @property
    def collect(self):
        """ Use with a with block to perform all logs within the block at once. """
        if OS.is_windows:
            # Having multiple threads or processes write to the same file is not
            # safe on Windows unlike on Linux or Mac, in the way that log.collect
            # is usually used. See https://stackoverflow.com/a/25924980.
            raise UnsupportedOS("Log collecting is not supported on windows")
        return _CollectLogs(self)

    def section(self, *tolog, with_info=True, sep=None, with_print=None, newline=True):
        """Log at SECTION level. See .log method for argument descriptions."""
        if newline:
            self._log("")
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.SECTION)

    def critical(self, *tolog, with_info=True, sep=None, with_print=None):
        """Log at CRITICAL level. See .log method for argument descriptions."""
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.CRITICAL)

    def error(self, *tolog, with_info=True, sep=None, with_print=None):
        """Log at ERROR level. See .log method for argument descriptions."""
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.ERROR)

    def warning(self, *tolog, with_info=True, sep=None, with_print=None):
        """Log at WARNING level. See .log method for argument descriptions."""
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.WARNING)

    def info(self, *tolog, with_info=True, sep=None, with_print=None):
        """Log at INFO level. See .log method for argument descriptions."""
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.INFO)

    def debug(self, *tolog, with_info=True, sep=None, with_print=None):
        """Log at DEBUG level. See .log method for argument descriptions."""
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.DEBUG)

    def __call__(self, *tolog, level=LogLevels.INFO, with_info=True, sep=None, with_print=None):
        """Shorthand for specific logging methods where level is specified as an argument."""
        self._log(*tolog, level=level, with_info=with_info, sep=sep, with_print=with_print)


log = Logger()
