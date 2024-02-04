from __future__ import annotations
from abc import ABC
from argparse import ArgumentParser, Namespace, SUPPRESS
from ast import literal_eval
from configparser import ConfigParser
from copy import deepcopy
from pprint import pformat
from shutil import rmtree
from typing import Any, Callable, Optional, TypeVar, Union
import io
import os
import re
import shlex
import sys

from pelutils import get_timestamp_for_files, except_keys


_T = TypeVar("_T")
_type = type  # Save `type` under different name to prevent name collisions

# Support for nargs is limited to 0 (any number of args) and set number
# As such, not all modes supported by argparse (see documentation) are supported here
# https://docs.python.org/3/library/argparse.html#nargs
_NargsTypes = Union[int, None]

def _fixdash(argname: str) -> str:
    """ Replaces dashes in argument names with underscores """
    return argname.replace("-", "_")

class ParserError(Exception):
    pass

class ConfigError(ParserError):
    pass

class AbstractArgument(ABC):
    """ Contains description of an argument.
    '--' is automatically prepended to `name` when given from the command line. """

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
            raise TypeError("'nargs' type must be one of %s, not %s" % (_NargsTypes.__args__, type(nargs)))
        if isinstance(nargs, int) and nargs < 0:
            raise ValueError("When expecting a set number of arguments, the number must be at least 0")

    def __str__(self) -> str:
        vars_str = ", ".join(f"{name}={value}" for name, value in vars(self).items())
        return f"{self.__class__.__name__}({vars_str})"

    def __hash__(self) -> int:
        return hash(self.name)

class Argument(AbstractArgument):
    """ Argument that must be given a value. """

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
            raise TypeError(f"Class {self.__class__.__name__} does not accept keyword argument 'default'")
        self.type = type
        self.metavar = metavar
        self.nargs = nargs

class Option(AbstractArgument):
    """ Optional argument with a default value. """

    def __init__(
        self,
        name:    str, *,
        default: _T | None                    = None,
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
        elif self.default is not None:
            if nargs is not None:
                self.default = list(self.default)
            self.type = _type(self.default) if nargs is None else _type(self.default[0])
            if nargs is not None and not all(isinstance(x, self.type) for x in self.default):
                raise ValueError("All elements in default value of %s must be of type %s" % (
                    name, self.type
                ))
        else:
            self.type = str
        self.metavar = metavar
        self.nargs = nargs

class Flag(AbstractArgument):
    """ Boolean flag. Defaults to `False` when not given and `True` when given. """

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

    document_filename = "used-config.ini"

    def __init__(self, name: str, location: str, explicit_args: set[str], docfile_content: str, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.location = location
        self.explicit_args = explicit_args
        self._docfile_content = docfile_content

    def todict(self) -> dict[str, Any]:
        """ Returns a dictionary version of itself which contains solely the parsed values. """
        d = vars(self)
        d = { kw: v for kw, v in d.items() if not kw.startswith("_") and kw not in { "config", "explicit_args" } }
        return d

    def prepare_directory(self, encoding: Optional[str] = None):
        """ Clears the job directory and puts a documentation file in it. """
        rmtree(self.location, ignore_errors=True)
        os.makedirs(self.location)
        self.write_documentation(encoding)

    def write_documentation(self, encoding: Optional[str] = None):
        """ Writes, or appends if one already exists, a documentation file in the location. The file has
        the CLI command user for running the program as a comment as well as the config file,
        if such a one was used. """
        os.makedirs(self.location, exist_ok=True)
        path = os.path.join(self.location, self.document_filename)
        with open(path, "a", encoding=encoding) as docfile:
            docfile.write(self._docfile_content)

    def __getitem__(self, key: str) -> Any:
        if key in self.__dict__:
            return self.__dict__[key]
        elif _fixdash(key) in self.__dict__:
            return self.__dict__[_fixdash(key)]
        else:
            raise KeyError("No such job argument '%s'" % key)

    def __str__(self) -> str:
        return pformat(self.todict())

ArgumentTypes = Union[Argument, Option, Flag]

class Parser:

    location: str | None = None  # Set in `parse` method

    _default_config_job = "DEFAULT"

    _location_arg = Argument("location")
    _location_arg.name_or_flags = lambda: ("location",)
    _name_arg = Option("name", default=None, help="Name of the job")
    _section_separator = ":"
    _encoding_separator = "::"
    _config_arg = Option(
        "config",
        default = None,
        abbrv   = "c",
        help    = "Path to config file. Encoding can be specified by giving <path>%s<encoding>,"
                  "e.g. --config path/to/config.ini%sutf-8" % (_encoding_separator, _encoding_separator),
    )

    _reserved_arguments: tuple[ArgumentTypes] = (_location_arg, _name_arg, _config_arg)
    _reserved_names = { arg.name for arg in _reserved_arguments }
    _reserved_names.add("help")  # Reserved by argparse
    _reserved_abbrvs = { arg.abbrv for arg in _reserved_arguments if arg.abbrv }

    @property
    def reserved_names(self):
        return self._reserved_names
    @property
    def reserved_abbrvs(self):
        return self._reserved_abbrvs
    @property
    def encoding_seperator(self):
        return self._encoding_separator

    def __init__(
        self,
        *arguments:  ArgumentTypes,
        description: str | None = None,
        multiple_jobs           = False,
    ):
        # Modifications are made to the argument objects, so make a deep copy
        arguments = tuple(deepcopy(arg) for arg in arguments)

        self._multiple_jobs = multiple_jobs

        self._argparser = ArgumentParser(description=description)
        self._configparser = ConfigParser(allow_no_value=True)
        self._configparser.optionxform = str

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

        self._location_arg.help = "Directory containing all job directories" if self._multiple_jobs else "Job directory"

        # Build abbrevations for arguments
        # Those with explicit abbreviations are handled first to prevent being overwritten
        _used_abbrvs = { "h" }  # Reserved by argparse
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
            # nargs is given as "*" to argparser to prevent it from raising errors
            # Input validity is then checked later
            if isinstance(argument, Argument):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    type     = argument.type,
                    help     = argument.help,
                    metavar  = argument.metavar,
                    nargs    = "*" if argument.nargs is not None else None,
                    **argument.kwargs,
                )
            elif isinstance(argument, Option):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    default  = argument.default,
                    type     = argument.type,
                    help     = argument.help,
                    metavar  = argument.metavar,
                    nargs    = "*" if argument.nargs is not None else None,
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
        """ Builds a dictionary that maps argument names to their default values.
        Arguments without defaults values are not included. """
        return { argname: arg.default
            for argname, arg
            in self._arguments.items()
            if hasattr(arg, "default") and arg.name not in self._reserved_names }

    def _parse_explicit_cli_args(self) -> set[str]:
        """ Returns a set of arguments explicitly given from the command line.
        No prepended dashes and in-word dashes have been changed to underscores. """
        # Create auxiliary parser to help determine if arguments are given explicitly from CLI
        # Heavily inspired by this answer: https://stackoverflow.com/a/45803037/13196863
        aux_parser = ArgumentParser(argument_default=SUPPRESS)
        args = self._argparser.parse_args()
        for argname in vars(args):
            arg = self._arguments[argname]
            if isinstance(arg, Flag):
                aux_parser.add_argument(*arg.name_or_flags(), action="store_true")
            else:
                aux_parser.add_argument(*arg.name_or_flags(), nargs="*" if arg.nargs is not None else None)
        explicit_cli_args = aux_parser.parse_args()

        return set(vars(explicit_cli_args))

    def _parse_config_file(self, config_path: str) -> dict[str, dict[str, Any]]:
        """ Parses a given configuration file (.ini format).
        Returns a dictionary where each section as a key pointing to corresponding argument/value pairs. """
        if self._encoding_separator in config_path:
            config_path, encoding = config_path.split(self._encoding_separator, maxsplit=1)
        else:
            encoding = None

        config_path, *sections = config_path.split(self._section_separator)
        sections = set(sections)

        if not self._configparser.read(config_path, encoding=encoding):
            raise FileNotFoundError("Configuration file not found at %s" % config_path)

        for section in sections:
            if section not in self._configparser:
                raise ParserError("Unable to parse unknown section '%s'" % section)

        # Save given values and convert to proper types
        config_dict = dict()
        for section, arguments in self._configparser.items():
            if sections and section not in sections and section != self._default_config_job:
                continue
            config_dict[section] = dict()
            for argname, value in arguments.items():
                argname = _fixdash(argname)
                if argname not in self._arguments:
                    raise ParserError("Unknown argument '%s'" % argname)
                if isinstance(self._arguments[argname], Flag):
                    # If flag value is given in config file, parse True/False
                    if isinstance(value, str):
                        config_dict[section][argname] = literal_eval(value)
                        # Check if valid value
                        if not isinstance(config_dict[section][argname], bool):
                            raise ValueError("Value %s in section %s must be 'True' or 'False', not '%s'" % (
                                argname, section, value
                            ))
                    else:
                        config_dict[section][argname] = True
                else:  # Arguments and options
                    # If multiple values, parse each as given type
                    # Otherwise, parse single argument as given type
                    if self._arguments[argname].nargs is not None:
                        config_dict[section][argname] = [self._arguments[argname].type(x) for x in shlex.split(value)]
                    else:
                        config_dict[section][argname] = self._arguments[argname].type(value)

        return config_dict

    def parse_args(self) -> JobDescription | list[JobDescription]:
        """ Parses command line arguments and optionally a configuration file if given.
        If multiple_jobs was set to True in __init__, a list of job descriptions is returned.
        Otherwise, a single job description is returned. """
        job_descriptions: list[JobDescription] = list()
        args = self._argparser.parse_args()
        explicit_cli_args = self._parse_explicit_cli_args()
        self.location = args.location

        if args.config is None:
            docfile_content = self._get_docfile_content()
            name = args.name or get_timestamp_for_files()
            if self._multiple_jobs:
                location = os.path.join(self.location, name)
            else:
                location = self.location
            arg_dict = vars(args)
            for argname, arg in self._arguments.items():
                if isinstance(arg, Argument) and arg_dict[argname] is None:
                    raise ParserError("Missing value for '%s'" % arg.name)

            job_descriptions.append(JobDescription(
                name            = name,
                location        = location,
                explicit_args   = explicit_cli_args,
                docfile_content = docfile_content,
                **except_keys(arg_dict, ("location", "name")),
            ))
        else:
            config_dict = self._parse_config_file(args.config)
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
                    location = os.path.join(self.location, name)
                else:
                    name = section if self._name_arg.name not in explicit_cli_args else args.name
                    location = self.location

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
                    name            = name,
                    location        = location,
                    explicit_args   = { *config_args.keys(), *explicit_cli_args },
                    docfile_content = docfile_content,
                    **value_dict,
                ))

        # Check if any arguments are missing or are invalid
        for job in job_descriptions:
            for argname, arg in self._arguments.items():
                argument = self._arguments[argname]
                if argname not in job:
                    raise ParserError("Job '%s' is missing value for '%s'" % (job.name, arg.name))
                elif hasattr(argument, "nargs") and argument.nargs is not None:
                    if job[argname] is None and isinstance(argument, Argument):
                        raise ParserError("Argument '%s' has not been given in job '%s'" % (
                            argname, job.name
                        ))
                    assert isinstance(job[argname], list)
                    assert all(isinstance(x, argument.type) for x in job[argname])
                    if argument.nargs > 0 and len(job[argname]) != argument.nargs:
                        raise ValueError("Argument '%s' in job '%s' should have %i args, but had %i" % (
                            argname, job.name, argument.nargs, len(job[argname])
                        ))

        return job_descriptions if self._multiple_jobs else job_descriptions[0]

    def _get_docfile_content(self) -> str:
        buffer = io.StringIO()
        self._configparser.write(buffer)
        lines: list[str] = [
            "CLI command",
            " ".join(sys.argv),
            "Default values",
            *pformat(self._get_default_values(), width=120).splitlines(),
        ]
        buffer.write(os.linesep + "# " + f"{os.linesep}# ".join(lines) + os.linesep)
        content = buffer.getvalue()
        buffer.close()
        return content
