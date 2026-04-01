"""Supporting elements to the logger, such as levels, colours, collection of logs, etc."""

from __future__ import annotations

from enum import IntEnum
from types import TracebackType

import pelutils.logging as logging_lib


class LogLevels(IntEnum):
    """Logging levels by priority."""

    SECTION = 5
    CRITICAL = 4
    ERROR = 3
    WARNING = 2
    INFO = 1
    DEBUG = 0


class LevelManager:
    """Used for context limiting logging levels.

    Example
    -------
    ```py
    with log.level(Levels.WARNING):
        log.error("This will be logged")
        log.info("This will not be logged")
    ```
    """

    def __init__(self):
        self.level: LogLevels | int | None = None

    def with_level(self, level: LogLevels | int) -> LevelManager:
        self.level = level
        return self

    def __enter__(self):
        pass

    def __exit__(self, *_):
        self.level = None


class LogErrors:
    """Used for catching exceptions with logger and logging them before reraising them."""

    def __init__(self, log: "logging_lib.Logger"):
        self._log = log

    def __enter__(self):
        pass

    def __exit__(self, et: type[BaseException] | None, ev: BaseException | None, tb: TracebackType | None):
        is_zero_exit_code = et is SystemExit and ev.code == 0  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
        if et and not is_zero_exit_code:
            self._log.log_with_stacktrace(ev, level=LogLevels.CRITICAL)  # pyright: ignore[reportArgumentType]


class CollectLogs:
    """Used for producing all logging output from a block at once.

    This is useful with threads, asynchronous code, and multiprocessing to prevent the logs getting mixed up.
    It is not supported on Windows.

    Example
    -------
    ```
    def fun():
        with log.collect:
            do stuff

    with mp.Pool() as p:
        p.map(fun, ...)
    ```
    """

    def __init__(self, logger: "logging_lib.Logger"):
        self._log = logger

    def __enter__(self):
        self._log._set_collect_mode(True)  # pyright: ignore[reportPrivateUsage]

    def __exit__(self, *_):
        self._log._log_collected()  # pyright: ignore[reportPrivateUsage]
        self._log._set_collect_mode(False)  # pyright: ignore[reportPrivateUsage]
