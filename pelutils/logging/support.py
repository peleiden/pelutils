""" This file contains supporting elements to the logger, such as levels,
colours, collection of logs, etc. """
from __future__ import annotations
from enum import IntEnum
from functools import update_wrapper
from typing import Callable, Optional


class LogLevels(IntEnum):
    """ Logging levels by priority. """
    SECTION  = 5
    CRITICAL = 4
    ERROR    = 3
    WARNING  = 2
    INFO     = 1
    DEBUG    = 0

class _LevelManager:
    """
    Used for context limiting logging levels, e.g.
    ```
    with log.level(Levels.WARNING):
        log.error("This will be logged")
        log.info("This will not be logged")
    ``` """

    def __init__(self):
        self.level: Optional[LogLevels] = None

    def with_level(self, level: LogLevels | int) -> _LevelManager:
        self.level = level
        return self

    def __enter__(self):
        pass

    def __exit__(self, *_):
        self.level = None

class _LogErrors:
    """ Used for catching exceptions with logger and logging them before reraising them. """

    def __init__(self, log):
        self._log = log

    def __enter__(self):
        pass

    def __exit__(self, et, ev, tb_):
        if et and self._log._collect:
            self._log.log_collected()
        if et:
            self._log.log_with_stacktrace(ev, level=LogLevels.CRITICAL)

class _CollectLogs:

    """ Wrap functions with this class to have them output all their output at once.
    Useful with multiprocessing, e.g.
    ```
    with mp.Pool() as p:
        p.map(log.collect(fun), ...)
    ``` """

    def __init__(self, logger, fun: Callable):
        self.logger = logger
        self.fun = fun

    def __call__(self, *args, **kwargs):
        self.logger.set_collect_mode(True)
        return_value = self.fun(*args, **kwargs)
        self.logger.log_collected()
        self.logger.set_collect_mode(False)
        return return_value
