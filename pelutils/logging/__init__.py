"""A colourful, feature-rich logger that prints and writes to a log file at once.

Python's built-in ``logging`` is powerful but fiddly to set up, and a bare ``print``
gives you no levels, no timestamps, and no file on disk. This logger aims for the sweet
spot: a single :meth:`Logger.configure` call and you get colour-coded, timestamped output
to both the console and a log file, with severity levels you can filter on the fly, log-file
rotation, one-line exception logging with full stacktraces, and safe log collection from
multiple processes.

Quick start
-----------

.. code-block:: python

    from pelutils.logging import log, LogLevels

    # Point the logger at a file (missing dirs are created). Omit the path to only print.
    log.configure("run.log")

    log.section("Starting run")     # Highlighted section header
    log("Loaded 1,000 rows")        # Logs at INFO level
    log.warning("Low on memory")
    log.debug("Batch size", 32)

    # Log any exception raised in the block, with its full stacktrace, then re-raise
    with log.log_errors:
        risky_operation()

``log`` is a ready-to-use global instance and is all most code needs; construct your own
with :class:`Logger` when you need several independent loggers. See :class:`Logger` for the
full API, including ``log.level``/``log.no_log`` for temporarily changing the level,
``log.collect`` for multiprocessing, ``log.input`` for logged user input, and rotation via
the ``rotation`` argument to ``configure``.
"""

from ._logger import LEVEL_FORMAT, TIMESTAMP_COLOR, Logger, LoggingException, log
from ._utils import LogLevels

__all__ = ("LEVEL_FORMAT", "TIMESTAMP_COLOR", "LogLevels", "Logger", "LoggingException", "log")
