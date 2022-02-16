from __future__ import annotations
from typing import Callable, Generator, Iterable, Optional
import os
import traceback as tb

from pelutils import get_repo, get_timestamp
from pelutils.format import RichString

from .support import LogLevels, _LevelManager, _LogErrors, _CollectLogs


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
    pass

class _Logger:
    """ A simple logger which creates a log file and pushes strings both to stdout and the log file.
    Main features include automatically logging errors and their stacktrace (see _Logger.log_errors),
    collecting logs for multiprocessing (see _Logger.collect), and colourful prints. """

    _selected_logger: str
    _maxlen = max(len(l.name) for l in LogLevels)
    _spacing = 4 * " "

    _yes = "yes"
    _no = "no"

    def __init__(self):
        self._log_errors = _LogErrors(self)
        self._collect = False
        self._collected_log: list[RichString] = list()
        self._collected_print: list[RichString] = list()

    def configure(
        self,
        fpath: str, *,                          # Path to logfile. Missing directories are created
        default_seperator    = "\n",            # Default seperator when logging multiple strings in a single call
        append               = False,           # Set to True to append to old log file instead of overwriting it
        print_level          = LogLevels.INFO,  # Highest level that will be printed. All will be logged. None for no print
    ):

        # Create logfile
        if fpath is not None:
            dirs = os.path.split(fpath)[0]
            if dirs:
                os.makedirs(dirs, exist_ok=True)
            with open(fpath, "a" if append else "w", encoding="utf-8") as logfile:
                logfile.write("")

        self._fpath = fpath
        self._level_mgr = _LevelManager()
        self._log_errors = _LogErrors(self)
        self._default_sep = default_seperator
        self._print_level = print_level

    def level(self, level: LogLevels):
        """ Log only at given level and above. Use with a with block. """
        return self._level_mgr.with_level(level)

    @property
    def no_log(self):
        """ Disable logging inside a with block. """
        return self._level_mgr.with_level(max(LogLevels)+1)

    @property
    def log_errors(self):
        """ Use in a with block. Any errors thrown within the block are logged with the full stacktrace. """
        return self._log_errors

    def __call__(self, *tolog, level=LogLevels.INFO, with_info=True, sep=None, with_print=None):
        """ Shorthand for specific logging methods where level is specified as an argument. """
        self._log(*tolog, level=level, with_info=with_info, sep=sep, with_print=with_print)

    def _write_to_log(self, content: RichString):
        if self._fpath is not None:
            with open(self._fpath, "a", encoding="utf-8") as logfile:
                logfile.write(f"{content}\n")

    @staticmethod
    def _format(s: str, format: str) -> str:
        return f"[{format}]{s}[/]"

    def _log(self, *tolog, level=LogLevels.INFO, with_info=True, sep=None, with_print=None):
        if self._level_mgr.level is not None and level < self._level_mgr.level:
            return
        sep = sep or self._default_sep
        with_print = level >= self._print_level if with_print is None else with_print
        time = get_timestamp()
        tolog = sep.join([str(x) for x in tolog])
        time_spaces = len(time) * " "
        level_format = level.name + (self._maxlen - len(level.name)) * " "
        space = self._spacing + self._maxlen * " " + self._spacing
        logs = tolog.split("\n")
        rs = RichString()
        if with_info and tolog:
            rs.add_string(
                f"{time}{self._spacing}{level_format}{self._spacing}",
                self._format(time, TIMESTAMP_COLOR) +\
                    self._spacing +\
                    self._format(level_format, LEVEL_FORMAT[level]) +\
                    self._spacing,
            )
            rs.add_string(logs[0])
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

    def log_with_stacktrace(self, error: Exception, level=LogLevels.ERROR):
        self._log(
            f"A {type(error)} was thrown with the following stacktrace:",
            tb.format_exc(),
            level=level,
            sep="\n",
            with_print=False,
        )

    def _input(self, prompt: str) -> str:
        self.info("Prompt: '%s'" % prompt, with_print=False)
        response = input(prompt)
        self.info("Input:  '%s'" % response, with_print=False)
        return response

    def input(self, prompt: str | Iterable[str] = "") -> str | Generator[str]:
        """ Get user input and log both prompt an input.
        If prompt is an iterable, a generator of user inputs will be returned. """
        self._log("Waiting for user input", with_print=False)
        if isinstance(prompt, str):
            return self._input(prompt)
        else:
            return (self._input(p) for p in prompt)

    @classmethod
    def bool_input(cls, answer: str, *, default: bool) -> bool | None:
        """ Validate user yes/no input. Returns None if input is not parsable. Example:
        ```
        answer = log.input("Do you like this question? [y/N] ")
        likes_answer = log.bool_input(answer, default=False)
        # User answered y/Y/yes/Yes/YES/yE etc.
        likes_answer == True
        # User answered nothing or n/N/no/No/nO/NO
        likes_answer == False
        # User answered something unparsable as yes/no
        likes_answer == None
        ``` """
        answer = answer.strip()
        if not answer:
            return default
        if cls._yes.startswith(answer.lower()):
            return True
        if cls._no.startswith(answer.lower()):
            return False

    def log_repo(self):
        """ Niceness method for logging the git repo that the code is run in. """
        repo, commit = get_repo()
        if repo is not None:
            self.debug(
                "Executing in repository %s" % repo,
                "Commit: %s\n" % commit,
            )
        else:
            self.debug("Unable to find repository that code was executed in")

    def collect(self, fun: Callable) -> Callable:
        """ Wrap a function with this to collect logs. This means that all logs in the function are
        only printed when the function is over, which is useful for multiprocessing. If using log.log_errors,
        any partially done functions will have their content logged before the error is raised. """
        return _CollectLogs(self, fun)

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

    def section(self, *tolog, with_info=True, sep=None, with_print=None, newline=True):
        if newline:
            self._log("")
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.SECTION)

    def critical(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.CRITICAL)

    def error(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.ERROR)

    def warning(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.WARNING)

    def info(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.INFO)

    def debug(self, *tolog, with_info=True, sep=None, with_print=None):
        self._log(*tolog, with_info=with_info, sep=sep, with_print=with_print, level=LogLevels.DEBUG)


log = _Logger()
