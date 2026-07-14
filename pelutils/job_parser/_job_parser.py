import io
import shlex
import sys
from argparse import SUPPRESS, ArgumentParser
from ast import literal_eval
from configparser import ConfigParser, MissingSectionHeaderError
from copy import deepcopy
from datetime import datetime
from pprint import pformat
from typing import Any

from pelutils.misc import OS, except_keys

from ._structs import ArgumentTypes, ConfigError, Flag, JobDescription, JobParserError, OptionalArg, RequiredArg, fixdash


class JobParser:
    """Resolve typed command-line arguments and INI configuration files into jobs.

    Declare values with :class:`RequiredArg`, :class:`OptionalArg`, and :class:`Flag`.
    Values supplied on the command line override configuration values, which override
    optional defaults. A configuration file may contain a ``[DEFAULT]`` section and
    named sections; named sections become individual jobs.

    Use :meth:`parse_job` when exactly one job is expected. Set ``multiple_jobs=True``
    and use :meth:`parse_jobs` when a configuration can select multiple named sections.
    """

    _default_config_job = "DEFAULT"

    _name_arg = OptionalArg("name", default=None, help="Name of the job")
    _section_separator = ":"
    _config_arg = OptionalArg(
        "config-file",
        default=None,
        abbrev="c",
        help="Path a config file which uses the .ini/.conf file format.",
    )

    _reserved_arguments: tuple[ArgumentTypes, ...] = (_name_arg, _config_arg)
    _reserved_names = {arg.name for arg in _reserved_arguments}  # noqa: RUF012
    _reserved_names.add("help")  # Reserved by argparse
    _reserved_abbreviations = {arg.abbrev for arg in _reserved_arguments if arg.abbrev}  # noqa: RUF012

    @property
    def reserved_names(self) -> set[str]:
        """Argument names which are reserved."""
        return self._reserved_names

    @property
    def reserved_abbreviations(self) -> set[str]:
        """Argument abbreviations which are reserved."""
        return self._reserved_abbreviations

    def __init__(
        self,
        *arguments: ArgumentTypes,
        description: str | None = None,
        multiple_jobs: bool = False,
    ):
        """Create a parser from typed argument declarations.

        Parameters
        ----------
        *arguments : RequiredArg | OptionalArg | Flag
            Application-specific argument declarations.
        description : str | None, optional
            Description displayed by the generated ``--help`` command.
        multiple_jobs : bool, optional
            Allow configurations with multiple named sections. Use :meth:`parse_jobs`
            to retrieve their job descriptions.
        """
        # Modifications are made to the argument objects, so make a deep copy
        arguments = tuple(deepcopy(arg) for arg in arguments)

        self._multiple_jobs = multiple_jobs

        self._argparser = ArgumentParser(description=description)
        self._configparser = ConfigParser(allow_no_value=True)
        self._configparser.optionxform = str  # pyright: ignore[reportAttributeAccessIssue]

        # Ensure that no conflicts exist with reserved arguments
        if any(arg.name in self._reserved_names for arg in arguments):
            raise JobParserError(f"An argument conflicted with one of the reserved arguments: {self._reserved_names}")
        if any(arg.abbrev in self._reserved_abbreviations for arg in arguments):
            raise JobParserError(f"An argument conflicted with one of the reserved abbreviations: {self._reserved_abbreviations}")

        # Map argument names to arguments with dashes replaced by underscores
        self._arguments = {fixdash(arg.name): arg for arg in self._reserved_arguments + arguments}
        if len(self._arguments) != len(self._reserved_arguments) + len(arguments):
            raise JobParserError(
                "Conflicting arguments found. Note that '-' and '_' are counted the same,so e.g. 'a-b' and 'a_b' would cause a conflict"
            )

        # Build abbreviations for arguments
        # Those with explicit abbreviations are handled first to prevent being overwritten
        _used_abbreviations = {"h"}  # Reserved by argparse
        _args_with_abbreviations_first = sorted(self._arguments, key=lambda arg: self._arguments[arg].abbrev is None)
        for argname in _args_with_abbreviations_first:
            argument = self._arguments[argname]
            if argument.abbrev and argument.abbrev not in _used_abbreviations:
                _used_abbreviations.add(argument.abbrev)
            elif argument.abbrev:
                raise JobParserError(f"Abbreviation '{argument.abbrev}' was used multiple times")
            # Autogenerate abbreviation
            # First argname[0] is tried. If it exists, the other casing is used if it does not exist
            elif argname[0] not in _used_abbreviations:
                argument.abbrev = argname[0]
                _used_abbreviations.add(argument.abbrev)
            elif argname[0].swapcase() not in _used_abbreviations:
                argument.abbrev = argname[0].swapcase()
                _used_abbreviations.add(argument.abbrev)

        # Finally, add all arguments to argparser
        for argument in self._arguments.values():
            # nargs is given as "*" to argparser to prevent it from raising errors
            # Input validity is then checked later
            if isinstance(argument, RequiredArg):
                self._argparser.add_argument(
                    *argument._name_or_flags(),  # pyright: ignore[reportPrivateUsage]
                    type=argument.type,
                    help=argument.help,
                    metavar=argument.metavar,
                    nargs="*" if argument.nargs is not None else None,
                    **argument.kwargs,
                )
            elif isinstance(argument, OptionalArg):
                self._argparser.add_argument(
                    *argument._name_or_flags(),  # pyright: ignore[reportPrivateUsage]
                    default=argument.default,
                    type=argument.type,
                    help=argument.help,
                    metavar=argument.metavar,
                    nargs="*" if argument.nargs is not None else None,
                    **argument.kwargs,
                )
            else:
                assert isinstance(argument, Flag)
                self._argparser.add_argument(
                    *argument._name_or_flags(),  # pyright: ignore[reportPrivateUsage]
                    action="store_true",
                    help=argument.help,
                    **argument.kwargs,
                )

    def _get_default_values(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Build a dictionary that maps argument names to their default values.

        Arguments without defaults values are not included.
        """
        return {
            argname: arg.default  # pyright: ignore[reportAttributeAccessIssue]
            for argname, arg in self._arguments.items()
            if hasattr(arg, "default") and arg.name not in self._reserved_names
        }

    def _parse_explicit_cli_args(self) -> set[str]:
        """Return a set of arguments explicitly given from the command line.

        No prepended dashes and in-word dashes have been changed to underscores.
        """
        # Create auxiliary parser to help determine if arguments are given explicitly from CLI
        # Heavily inspired by this answer: https://stackoverflow.com/a/45803037/13196863
        aux_parser = ArgumentParser(argument_default=SUPPRESS)
        args = self._argparser.parse_args()
        for argname in vars(args):
            arg = self._arguments[argname]
            if isinstance(arg, Flag):
                aux_parser.add_argument(*arg._name_or_flags(), action="store_true")  # pyright: ignore[reportPrivateUsage]
            else:
                aux_parser.add_argument(*arg._name_or_flags(), nargs="*" if arg.nargs is not None else None)  # pyright: ignore[reportPrivateUsage]
        explicit_cli_args = aux_parser.parse_args()

        return set(vars(explicit_cli_args))

    def _parse_config_file(self, config_path: str) -> dict[str, dict[str, Any]]:  # noqa: PLR0912  # pyright: ignore[reportExplicitAny]
        """Parse a given configuration file (.ini format).

        Return a dictionary where each section as a key pointing to corresponding argument/value pairs.
        """
        config_path, *sections = config_path.split(self._section_separator)
        if len(config_path) == 1 and config_path.isalpha() and OS.is_windows:
            # Fix Windows drive letter issue
            config_path = f"{config_path}:{sections[0]}"
            sections = sections[1:]
        sections = set(sections)

        try:
            if not self._configparser.read(config_path):
                raise FileNotFoundError(f"Configuration file not found at {config_path}")
        except MissingSectionHeaderError as e:
            raise ConfigError(
                "The provided config file contains no section headers. This is best resolved by adding `[DEFAULT]` at the very top."
            ) from e

        for section in sections:
            if section not in self._configparser:
                raise JobParserError(f"Unable to parse unknown section '{section}'")

        # Save given values and convert to proper types
        config_dict = dict()
        for section, arguments in self._configparser.items():
            if sections and section not in sections and section != self._default_config_job:
                continue
            config_dict[section] = dict()
            for argname, value in arguments.items():
                argname = fixdash(argname)  # noqa: PLW2901
                if argname not in self._arguments:
                    raise JobParserError(f"Unknown argument '{argname}'")
                if isinstance(self._arguments[argname], Flag):
                    # If flag value is given in config file, parse True/False
                    if isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                        config_dict[section][argname] = literal_eval(value)
                        # Check if valid value
                        if not isinstance(config_dict[section][argname], bool):
                            raise ValueError(f"Value {argname} in section {section} must be 'True' or 'False', not '{value}'")
                    else:
                        assert value is None
                        config_dict[section][argname] = True
                else:  # Arguments and options
                    # If multiple values, parse each as given type
                    # Otherwise, parse single argument as given type
                    try:
                        if self._arguments[argname].nargs is not None:  # pyright: ignore[reportAttributeAccessIssue]
                            config_dict[section][argname] = [self._arguments[argname].type(x) for x in shlex.split(value)]  # pyright: ignore[reportAttributeAccessIssue, reportCallIssue]
                        else:
                            config_dict[section][argname] = self._arguments[argname].type(value)  # pyright: ignore[reportCallIssue, reportAttributeAccessIssue]
                    except ValueError as e:
                        raise ValueError(f"Unable to parse value '{argname}' in section '{section}': {e.args[0]}") from e

        return config_dict

    def _parse_jobs(self) -> list[JobDescription]:  # noqa: PLR0912
        """Parse command line arguments and optionally a configuration file if given.

        If multiple_jobs was set to True in __init__, a list of job descriptions is returned.
        Otherwise, a single job description is returned.
        """
        job_descriptions: list[JobDescription] = list()
        args = self._argparser.parse_args()
        explicit_cli_args = self._parse_explicit_cli_args()

        if args.config_file is None:
            docfile_content = self._get_docfile_content()
            name = args.name or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            arg_dict = vars(args)
            for argname, arg in self._arguments.items():
                if isinstance(arg, RequiredArg) and arg_dict[argname] is None:
                    raise JobParserError(f"Missing value for '{arg.name}'")

            job_descriptions.append(
                JobDescription(
                    name=name,
                    explicit_args=explicit_cli_args,
                    docfile_content=docfile_content,
                    **except_keys(arg_dict, ("name",)),
                )
            )
        else:
            config_dict = self._parse_config_file(args.config_file)
            # Update documentation file docname
            docfile_content = self._get_docfile_content()
            # If any section other than DEFAULT is given, then the sections consist of DEFAULT and the others
            # In that case the DEFAULT is not used and is thus discarded
            if len(config_dict) > 1:
                del config_dict[self._default_config_job]
            if len(config_dict) > 1 and not self._multiple_jobs:
                raise ConfigError("Multiple sections found in config file, yet multiple_jobs has been set to `False`")

            # Create job descriptions section-wise
            for section, config_args in config_dict.items():
                if self._multiple_jobs:
                    name = section
                    if section == self._default_config_job:
                        name = section if self._name_arg.name not in explicit_cli_args else args.name
                else:
                    name = section if self._name_arg.name not in explicit_cli_args else args.name

                # Final values of all arguments
                # No prepended dashes, but in-word dashes have been changed to underscores
                value_dict = {
                    **except_keys(
                        self._get_default_values(),
                        ("name", "config"),
                    ),
                    **config_args,
                    **{argname: value for argname, value in except_keys(vars(args), ("name",)).items() if argname in explicit_cli_args},
                }
                job_descriptions.append(
                    JobDescription(
                        name=name,
                        explicit_args={*config_args.keys(), *explicit_cli_args},
                        docfile_content=docfile_content,
                        **value_dict,
                    )
                )

        # Check if any arguments are missing or are invalid
        for job in job_descriptions:
            for argname, arg in self._arguments.items():
                argument = self._arguments[argname]
                if argname not in job:
                    raise JobParserError(f"Job '{job.name}' is missing value for '{arg.name}'")
                elif isinstance(argument, (RequiredArg, OptionalArg)) and argument.nargs is not None:
                    if job[argname] is None and isinstance(argument, RequiredArg):
                        raise JobParserError(f"Argument '{argname}' has not been given in job '{job.name}'")
                    assert isinstance(job[argname], list) or job[argname] is None
                    if job[argname] is not None:
                        assert all(isinstance(x, argument.type) for x in job[argname])  # pyright: ignore[reportArgumentType]
                        if argument.nargs > 0 and len(job[argname]) != argument.nargs:
                            raise ValueError(
                                f"Mandatory argument '{argname}' expected {argument.nargs} values but received {len(job[argname])}"
                            )

        return job_descriptions

    def parse_job(self) -> JobDescription:
        """Parse command-line and configuration input into exactly one job.

        Use this method for a normal one-job invocation. It also works with a selected
        single section when ``multiple_jobs=True``. Command-line values take precedence
        over configuration values.

        Raises
        ------
        ConfigError
            If the selected configuration resolves to multiple jobs.
        """
        jobs = self._parse_jobs()
        if len(jobs) != 1:
            raise ConfigError("Multiple jobs were resolved; use parse_jobs() instead")
        return jobs[0]

    def parse_jobs(self) -> list[JobDescription]:
        """Parse command-line and configuration input into one or more jobs.

        This method requires ``multiple_jobs=True`` when the configuration resolves to
        multiple named sections. A command-line-only invocation returns a one-item list.
        """
        return self._parse_jobs()

    def _get_docfile_content(self) -> str:
        buffer = io.StringIO()
        buffer.write(f"# Running job at {datetime.now()}\n")
        lines: list[str] = [
            "CLI command",
            " ".join(sys.argv),
            "Default values",
            *pformat(self._get_default_values(), width=120).splitlines(),
        ]
        buffer.write("\n# " + "\n# ".join(lines) + "\n")
        cline = "# Used config file\n"
        buffer.write(cline)
        position = buffer.tell()
        self._configparser.write(buffer)
        if buffer.tell() == position:
            # Nothing was written to the buffer, so clear the config file section
            buffer.seek(position - len(cline))
            buffer.truncate()
            buffer.write(2 * "\n")
        content = buffer.getvalue()
        buffer.close()
        return content
