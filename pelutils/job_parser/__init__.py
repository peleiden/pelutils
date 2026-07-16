"""Typed argument and configuration parsing that treats a run as a *job*.

``argparse`` handles command-line flags but knows nothing about config files, so the
moment you want to save a run's settings, reproduce it later, or launch a sweep of
several runs, you end up hand-rolling a config file parser, merging it with the CLI args by
hand, and writing your own record of what was actually run. :class:`JobParser` does all
of that: you declare your arguments once with a type, and it resolves values from the
command line *and* an INI config file into one or more :class:`JobDescription` objects —
CLI values overriding config values, which override declared defaults. A single config
file can describe many named jobs, and every resolved job can write out an exact,
human-readable record of how it was invoked.

Quick start
-----------

.. code-block:: python

    from pathlib import Path
    from pelutils.job_parser import Flag, JobParser, OptionalArg, RequiredArg

    parser = JobParser(
        RequiredArg("data-path", help="Training data directory"),
        OptionalArg("learning-rate", default=1e-4, type=float, help="Optimizer learning rate"),
        Flag("fp16", help="Use mixed precision"),
        multiple_jobs=True,
    )

    for job in parser.parse_jobs():
        # Names are --kebab-case on the CLI and snake_case attributes on the job
        print(job.name, job.data_path, job.learning_rate, job.fp16)
        job.write_documentation(Path("runs") / job.name / "arguments.ini")
        ...  # Run your application with the resolved job values

Declare :class:`RequiredArg` for values every job must supply, :class:`OptionalArg` for
values with a default, and :class:`Flag` for booleans. Point the parser at a config file
with ``--config-file config.ini``; a file may contain a shared ``[DEFAULT]`` section plus
named sections that each become a job. Target a single section directly with
``--config-file config.ini:section-name``. A config file for the parser above might look
like:

.. code-block:: ini

    [DEFAULT]
    data-path = /data/train    # Shared by every job below

    [baseline]
    # Inherits the default learning rate; fp16 as a bare key means True
    fp16

    [high-lr]
    learning-rate = 5e-4

For the common single-job case, drop ``multiple_jobs=True`` and call :meth:`JobParser.parse_job`
to get one :class:`JobDescription` back. See :class:`JobParser` for the full API and
:meth:`JobDescription.write_documentation` for auto-documenting a run.
"""

from ._job_parser import JobParser
from ._structs import ArgumentTypes, ConfigError, Flag, JobDescription, JobParserError, OptionalArg, RequiredArg

__all__ = ("ArgumentTypes", "ConfigError", "Flag", "JobDescription", "JobParser", "JobParserError", "OptionalArg", "RequiredArg")
