""" This file contains supporting elements to the logger, such as levels,
colours, collection of logs, etc. """
from __future__ import annotations

from enum import IntEnum
from typing import Optional


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

    def __exit__(self, et, ev, _):
        is_zero_exit_code = et is SystemExit and ev.code == 0
        if et and not is_zero_exit_code:
            self._log.log_with_stacktrace(ev, level=LogLevels.CRITICAL)

class _CollectLogs:

    """ Used for producing all logging output from a block at once. This is useful with
    multiprocessing to prevent the logs getting mixed up.
    ```
    def fun():
        with log.collect:
            do stuff

    with mp.Pool() as p:
        p.map(fun, ...)
    ``` """

    def __init__(self, logger):
        self._log = logger

    def __enter__(self):
        self._log._set_collect_mode(True)

    def __exit__(self, *_):
        self._log._log_collected()
        self._log._set_collect_mode(False)
