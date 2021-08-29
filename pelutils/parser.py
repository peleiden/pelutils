from __future__ import annotations
from abc import ABC
from argparse import ArgumentParser, Namespace, SUPPRESS
from ast import literal_eval
from configparser import ConfigParser
from copy import deepcopy
from shutil import rmtree
from typing import Any, Callable, TypeVar, Union
import os
import re
import sys

from pelutils import get_timestamp, except_keys

# TODO Support for nargs
# Make sure that it works better than click that only allows one narg argument
# TODO Assert that no unknown arguments are given


_T = TypeVar("_T")
_type = type  # Save `type` under different name to prevent name collisions

_NargsTypes = Union[str, int, None]

def _fixdash(argname: str) -> str:
    """ Replaces dashes in argument names with underscores """
    return argname.replace("-", "_")

class ParserError(Exception):
    pass

class CLIError(ParserError):
    pass

class ConfigError(ParserError):
    pass

class AbstractArgument(ABC):
    """ Contains description of an argument
    '--' is automatically prepended to `name` when given from the command line """

    def __init__(self, name: str, abbrv: str | None, help: str | None, **kwargs):
        self._validate(name, abbrv)

        self.name   = name
        self.abbrv  = abbrv
        self.help   = help
        self.kwargs = kwargs

    @staticmethod
    def _validate(name: str, abbrv: str | None):
        if not name:
            raise ValueError("name must not be an empty string")
        if name.startswith("-"):
            raise ValueError("Double dashes are automatically prepended and should not be given by user: '%s'" % name)
        if isinstance(abbrv, str) and (len(abbrv) != 1 or not abbrv.isalpha()):
            raise ValueError("abbrv must be an alpha character and have length 1: '%s'" % abbrv)
        if re.search(r"\s", name):
            raise ValueError("name cannot contain whitespace")

    def name_or_flags(self) -> tuple[str, ...]:
        if self.abbrv:
            return ("-" + self.abbrv, "--" + self.name)
        else:
            return ("--" + self.name,)

    @staticmethod
    def _validate_nargs(nargs: _NargsTypes):
        if type(nargs) not in _NargsTypes.__args__:
            raise TypeError("'nargs' must be one of %s, not %s" % (_NargsTypes.__args__, type(nargs)))
        if isinstance(nargs, str) and nargs not in { "?", "*", "+" }:
            raise ValueError("When 'nargs' is a string, it must be one of the following: '?', '*', '+'")

    def __str__(self) -> str:
        vars_str = ", ".join(f"{name}={value}" for name, value in vars(self).items())
        return f"{self.__class__.__name__}({vars_str})"

    def __hash__(self) -> int:
        return hash(self.name)

class Argument(AbstractArgument):
    """ Argument that must be given a value
    See documentation possible values of `nargs`
    https://docs.python.org/3/library/argparse.html#nargs """

    def __init__(
        self,
        name:    str, *,
        type:    Callable[[str], _T]          = str,
        abbrv:   str | None                   = None,
        help:    str | None                   = None,
        metavar: str | tuple[str, ...] | None = None,
        nargs:   _NargsTypes                  = None,
        **kwargs,
    ):
        super().__init__(name, abbrv, help=help, **kwargs)
        self._validate_nargs(nargs)
        if "default" in kwargs:
            raise TypeError("Argument() does not accept keyword argument 'default'")
        self.type = type
        self.metavar = metavar
        self.nargs = nargs

class Option(AbstractArgument):
    """ Optional argument with a default value
    See documentation possible values of `nargs`
    https://docs.python.org/3/library/argparse.html#nargs """

    def __init__(
        self,
        name:    str, *,
        default: _T | None,
        type:    Callable[[str], _T] | None   = None,
        abbrv:   str | None                   = None,
        help:    str | None                   = None,
        metavar: str | tuple[str, ...] | None = None,
        nargs:   _NargsTypes                  = None,
        **kwargs,
    ):
        super().__init__(name, abbrv, help, **kwargs)
        self._validate_nargs(nargs)

        self.default = default
        if type is not None:
            self.type = type
        elif default is not None:
            self.type = _type(default)
        else:
            self.type = str
        self.metavar = metavar
        self.nargs = nargs

class Flag(AbstractArgument):
    """ Boolean flag. Defaults to `False` when not given and `True` when given """

    def __init__(
        self,
        name:  str, *,
        abbrv: str | None = None,
        help:  str | None = None,
        **kwargs,
    ):
        super().__init__(name, abbrv, help, **kwargs)

    @property
    def default(self):
        return False

class JobDescription(Namespace):

    def __init__(self, name: str, location: str, explicit_args: set[str], **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.location = location
        self.explicit_args = explicit_args

    def todict(self) -> dict[str, Any]:
        return vars(self)

    def __getitem__(self, key: str) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        elif _fixdash(key) in self.__dict__:
            return self.__dict__[_fixdash(key)]
        else:
            raise KeyError("No such job argument '%s'" % key)

ArgumentTypes = Union[Argument, Option, Flag]

class Parser:

    location: str | None = None  # Set in `parse` method

    _default_config_job = "DEFAULT"

    _location_arg = Argument("location", help="Job folder if multiple_jobs is False else folder containing all job folders")
    _location_arg.name_or_flags = lambda: ("location",)
    _name_arg = Option("name", default=None, abbrv="n", help="Name of the job")
    _encoding_sep = "::"
    _config_arg = Option(
        "config",
        default = None,
        abbrv   = "c",
        help    = "Path to config file. Encoding can be specified by giving <path>%s<encoding>,"
                  "e.g. --config path/to/config.ini%sutf-8" % (_encoding_sep, _encoding_sep),
    )

    _reserved_arguments: tuple[ArgumentTypes] = (_location_arg, _name_arg, _config_arg)
    _reserved_names  = { arg.name for arg in _reserved_arguments }
    _reserved_abbrvs = { arg.abbrv for arg in _reserved_arguments if arg.abbrv }
    @property
    def reserved_names(self):
        return self._reserved_names
    @property
    def reserved_abbrvs(self):
        return self._reserved_abbrvs

    def __init__(
        self,
        *arguments:  ArgumentTypes,
        description: str | None = None,
        multiple_jobs = False,
    ):
        # Modifications are made to the argument objects, so make a deep copy
        arguments = tuple(deepcopy(arg) for arg in arguments)

        self._multiple_jobs = multiple_jobs

        self._argparser = ArgumentParser(description=description)
        self._configparser = ConfigParser(allow_no_value=True)

        # Ensure that no conflicts exist with reserved arguments
        if any(arg.name in self._reserved_names for arg in arguments):
            raise ParserError("An argument conflicted with one of the reserved arguments: %s" % self._reserved_names)
        if any(arg.abbrv in self._reserved_abbrvs for arg in arguments):
            raise ParserError("An argument conflicted with one of the reserved abbreviations: %s" % self._reserved_abbrvs)

        # Map argument names to arguments with dashes replaced by underscores
        self._arguments = { _fixdash(arg.name): arg for arg in self._reserved_arguments + arguments }
        if len(self._arguments) != len(self._reserved_arguments) + len(arguments):
            raise ParserError("Conflicting arguments found. Notice that '-' and '_' are counted the same,"
                "so e.g. 'a-b' and 'a_b' would cause a conflict")
        # Build abbrevations for arguments
        # Those with explicit abbreviations are handled first to prevent being overwritten
        _used_abbrvs = set()
        _args_with_abbrvs_first = sorted(self._arguments, key=lambda arg: self._arguments[arg].abbrv is None)
        for argname in _args_with_abbrvs_first:
            argument = self._arguments[argname]
            if argument.abbrv and argument.abbrv not in _used_abbrvs:
                _used_abbrvs.add(argument.abbrv)
            elif argument.abbrv:
                raise ParserError("Abbreviation '%s' was used multiple times" % argument.abbrv)
            else:
                # Autogenerate abbreviation
                # First argname[0] is tried. If it exists, the other casing is used if it does not exist
                if argname[0] not in _used_abbrvs:
                    argument.abbrv = argname[0]
                    _used_abbrvs.add(argument.abbrv)
                elif argname[0].swapcase() not in _used_abbrvs:
                    argument.abbrv = argname[0].swapcase()
                    _used_abbrvs.add(argument.abbrv)

        # Finally, add all arguments to argparser
        for argument in self._arguments.values():
            # Add argument
            # FIXME nargs cannot be handled so explicitly by argparser
            # Possible solution: Coerce some nargs values into less restrictive ones
            # Then parse config, and finally check against original nargs values
            if isinstance(argument, Argument):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    type     = argument.type,
                    help     = argument.help,
                    metavar  = argument.metavar,
                    nargs    = argument.nargs,
                    **argument.kwargs,
                )
            elif isinstance(argument, Option):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    default  = argument.default,
                    type     = argument.type,
                    help     = argument.help,
                    metavar  = argument.metavar,
                    nargs    = argument.nargs,
                    **argument.kwargs,
                )
            elif isinstance(argument, Flag):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    action   = "store_true",
                    help     = argument.help,
                    **argument.kwargs,
                )

    def _get_default_values(self) -> dict[ArgumentTypes, Any]:
        """ Builds a dictionary that maps argument names to their default values
        Arguments without defaults values are not included """
        return { argname: arg.default
            for argname, arg
            in self._arguments.items()
            if hasattr(arg, "default") }

    def _parse_explicit_cli_args(self) -> set[str]:
        """ Returns a set of arguments explicitly given from the command line
        No prepended dashes and in-word dashes have been changed to underscores """
        # Create auxiliary parser to help determine if arguments are given explicitly from CLI
        # Heavily inspired by this answer: https://stackoverflow.com/a/45803037/13196863
        aux_parser = ArgumentParser(argument_default=SUPPRESS)
        args = self._argparser.parse_args()
        for argname in vars(args):
            arg = self._arguments[argname]
            if isinstance(arg, Flag):
                aux_parser.add_argument(*arg.name_or_flags(), action="store_true")
            else:
                aux_parser.add_argument(*arg.name_or_flags())
        explicit_cli_args = aux_parser.parse_args()

        return set(vars(explicit_cli_args))

    def _parse_config_file(self, config_path: str) -> dict[str, dict[str, Any]]:
        """ Parses a given configuration file (.ini format)
        Returns a dictionary where each section as a key pointing to corresponding argument/value paris """
        if self._encoding_sep in config_path:
            config_path, encoding = config_path.split(self._encoding_sep)
        else:
            encoding = None
        if not self._configparser.read(config_path, encoding=encoding):
            raise FileNotFoundError("Configuration file not found at %s" % config_path)

        # Save given values and convert to proper types
        config_dict = dict()
        for section, arguments in self._configparser.items():
            config_dict[section] = dict()
            for argname, value in arguments.items():
                argname = _fixdash(argname)
                if value is None or value in ("True", "False"):  # Flags
                    if isinstance(value, str):
                        config_dict[section][argname] = literal_eval(value)
                    else:
                        config_dict[section][argname] = True
                else:  # Arguments and options
                    config_dict[section][argname] = self._arguments[argname].type(value)

        return config_dict

    def parse_args(self, *, clear_folders=False) -> JobDescription | list[JobDescription]:
        """ Parses command line arguments and optionally a configuration file if given
        If multiple_jobs was set to True in __init__, a list of job descriptions is returned
        Otherwise, a single job description is returned
        If clear_folders is True, all job locations are cleared,
        such that an empty directory for each job is guaranteed """
        job_descriptions: list[JobDescription] = list()
        args = self._argparser.parse_args()
        explicit_cli_args = self._parse_explicit_cli_args()
        self.location = args.location

        if args.config is None:
            name = args.name or get_timestamp(for_file=True)
            if self._multiple_jobs:
                location = os.path.join(self.location, name)
            else:
                location = self.location
            arg_dict = vars(args)
            job_descriptions.append(JobDescription(
                name          = name,
                location      = location,
                explicit_args = explicit_cli_args,
                **except_keys(arg_dict, ("location", "name")),
            ))
        else:
            config_dict = self._parse_config_file(args.config)
            # If any section other than DEFAULT is given, then the sections consist of DEFAULT and the others
            # In that case the DEFAULT is not used and is thus discarded
            if len(config_dict) > 1:
                del config_dict["DEFAULT"]
            if len(config_dict) > 1 and not self._multiple_jobs:
                raise ConfigError("Multiple sections found in config file, yet multiple_jobs has been set to `False`")
            if self._multiple_jobs and self._name_arg.name in explicit_cli_args:
                raise CLIError("When configuring multiple jobs, `name` cannot be set from the command line")

            # Create job descriptions section-wise
            for section, config_args in config_dict.items():
                if self._multiple_jobs:
                    name = section
                    location = os.path.join(self.location, section)
                else:
                    name = section if self._name_arg.name not in explicit_cli_args else args.name
                    location = self.location
                    print(location)

                # Final values of all arguments
                # No prepended dashes, but in-word dashes have been changed to underscores
                value_dict = {
                    **except_keys(
                        self._get_default_values(),
                        ("name", "config"),
                    ),
                    **config_args,
                    **{ argname: value
                        for argname, value
                        in except_keys(vars(args), ("name", "location")).items()
                        if argname in explicit_cli_args },
                }
                job_descriptions.append(JobDescription(
                    name          = name,
                    location      = location,
                    explicit_args = { *config_args.keys(), *explicit_cli_args },
                    **value_dict,
                ))

        # Check if any arguments are missing
        for job in job_descriptions:
            for argname in self._arguments:
                if argname not in job:
                    raise ParserError("Job '%s' missing argument '%s'" % (job.name, argname))

        if clear_folders:
            for description in job_descriptions:
                rmtree(description.location, ignore_errors=True)
                os.makedirs(description.location)

        return job_descriptions if self._multiple_jobs else job_descriptions[0]

    def document(self, encoding: str | None=None) -> str:
        """ Saves the config file used to run the script containing the CLI command used to start the program as a comment
        If no config file was used, the CLI command comment is still present
        The path of the file is returned """
        filename = "given-arguments.ini"
        path = os.path.join(self.location, filename)
        with open(path, "w", encoding=encoding) as docfile:
            self._configparser.write(docfile)
            docfile.write(
                "\n" +
                "# CLI command:\n" +
                "# " + " ".join(sys.argv) + "\n" +
                "# Defaults at runtime: %s\n" % self._get_default_values()
            )
