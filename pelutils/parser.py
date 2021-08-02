from __future__ import annotations
from abc import ABC
from argparse import ArgumentError, ArgumentParser, Namespace, SUPPRESS
from configparser import ConfigParser
from shutil import rmtree
from typing import Any, Callable, Iterable, TypeVar, Union
# TODO Support for nargs
# Make sure that it works better than click that only allows one narg argument
# TODO Choices

# Challenges
# 1 Explicitly given arguments. There does not seem to be a proper way to do this with argparse
# Some possible solutions here: https://stackoverflow.com/questions/32056910/how-to-find-out-if-argparse-argument-has-been-actually-specified-on-command-line
# Overwriting action may be the most elegant solution, but this should also work with bools
# 2 Non-optional arguments. Setting non-optional arguments in argparse does not work as they then will have to be given explicitly from CLI
# A way to solve this is to let them all be optional in argparse and checking if they are given explicitly after parsing. If not, an error is raised
# Doing it this way also allows giving arguments using the keyword --argname syntax which is nicer
# `location` should be ignored as that should always be given as the first argument from the CLI
# This requires solving the above challenge


_T = TypeVar("_T")

def _fixdash(argname: str) -> str:
    """ Replaces dashes in argument names with underscores """
    return argname.replace("-", "_")

class AbstractArgument(ABC):

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

    def name_or_flags(self) -> tuple[str, ...]:
        if self.abbrv:
            return ("-" + self.abbrv, "--" + self.name)
        else:
            return ("--" + self.name,)

    def __hash__(self) -> int:
        return hash(self.name)

class Argument(AbstractArgument):

    def __init__(
        self,
        name:    str, *,
        type:    Callable[[str], _T] = str,
        help:    str | None = None,
        metavar: str | tuple[str, ...] | None = None,
        **kwargs,
    ):
        super().__init__(name, None, help=help, **kwargs)
        self.type = type
        self.metavar = metavar

class Option(AbstractArgument):

    def __init__(
        self,
        name:    str, *,
        default: _T | None,
        type:    Callable[[str], _T] = str,
        abbrv:   str | None = None,
        help:    str | None = None,
        metavar: str | tuple[str, ...] | None = None,
        **kwargs,
    ):
        super().__init__(name, abbrv, help, **kwargs)
        self.default = default
        self.type = type
        self.metavar = metavar

class Flag(AbstractArgument):

    def __init__(
        self,
        name:  str, *,
        abbrv: str | None = None,
        help:  str | None = None,
        **kwargs,
    ):
        super().__init__(name, abbrv, help, **kwargs)

class JobArguments(Namespace):

    def __init__(self, name: str, location: str):
        self.name = name
        self.location = location

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
    _location_arg.name_or_flags = lambda self: ("location",)
    _name_arg = Option("name", default=None, abbrv="n", help="Name of the job")
    _config_arg = Option("config", default=None, abbrv="c", help="Path to config file")

    _reserved_arguments: set[ArgumentTypes] = { _location_arg, _name_arg, _config_arg }
    reserved_names = { arg.name for arg in _reserved_arguments }
    reserved_abbrvs = { arg.abbrv for arg in _reserved_arguments if arg.abbrv }

    def __init__(
        self,
        arguments:   Iterable[ArgumentTypes],
        description: str | None = None,
        multiple_jobs = False,
        clear_folders = True,
    ):
        arguments = tuple(arguments)
        self._multiple_jobs = multiple_jobs
        self._clear_folders = clear_folders

        self._argparser = ArgumentParser(description=description)
        self._configparser = ConfigParser()

        # Ensure that no conflicts exist with reserved arguments
        if any(arg.name in self.reserved_names for arg in arguments):
            raise ArgumentError("An argument conflicted with one of the reserved arguments: %s" % self.reserved_names)
        if any(arg.abbrv in self.reserved_abbrvs for arg in arguments):
            raise ArgumentError("An argument conflicted with one of the reserved abbreviations: %s" % self.reserved_abbrvs)

        # Add all arguments to argparser
        # Map argument names to arguments with dashes replaced by underscores
        self._arguments = { _fixdash(arg.name): arg for arg in self._reserved_arguments }
        # Map argument abbreviations to arguments
        self._abbrvs = { arg.abbrv: arg for arg in self._reserved_arguments if arg.abbrv }
        for argument in self._arguments:
            # Add abbreviation and maybe autogenerate one
            if argument.abbrv and argument.abbrv not in self._abbrvs:
                self._abbrvs[argument.abbrv] = argument
            elif argument.abbrv and argument.abbrv in self._abbrvs:
                raise ArgumentError("Abbreviation '%s' was used twice" % argument.abbrv)
            elif not argument.abbrv:
                # Autogenerate abbreviations, first with lower case and then upper case if lower is taken
                if argument.name[0].lower() not in self._abbrvs:
                    argument.abbrv = argument.name[0].lower()
                    self._abbrvs[argument.abbrv] = argument
                elif argument.name[0].upper() not in self._abbrvs:
                    argument.abbrv = argument.name[0].upper()
                    self._abbrvs[argument.abbrv] = argument

            # Add argument
            if isinstance(argument, Argument):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    type     = argument.type,
                    help     = argument.help,
                    metavar  = argument.metavar,
                    required = True,
                    **argument.kwargs,
                )
            elif isinstance(argument, Option):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    default  = argument.default,
                    type     = argument.type,
                    help     = argument.help,
                    metavar  = argument.metavar,
                    required = False,
                    **argument.kwargs,
                )
            elif isinstance(argument, Flag):
                self._argparser.add_argument(
                    *argument.name_or_flags(),
                    action   = "store_true",
                    help     = argument.help,
                    required = False,
                    **argument.kwargs,
                )
            self._arguments[_fixdash(argument.name)] = argument

    def _parse_explicit_cli_args(self) -> dict[str, Any]:
        """ Returns a dictionary of arguments explicitly given from the command line """
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

        return vars(explicit_cli_args)

    def parse(self) -> JobArguments | list[JobArguments]:
        """ Parses command line arguments and optionally a configuration file if given
        If multiple_jobs was set to True in __init__, a list of job descriptions is returned
        Otherwise, a single job description is returned """
        job_descriptions: list[JobArguments] = list()
        args = self._argparser.parse_args()
        self.location = args.location
        # TODO Create job descriptions

        if self._clear_folders:
            for description in job_descriptions:
                rmtree(description.location, ignore_errors=True)

        return job_descriptions if self._multiple_jobs else job_descriptions[0]

    def document(self) -> str:
        """ Saves the config file used to run the script containing the CLI command used to start the program as a comment
        If no config file was used, the CLI command comment is still present
        The path of the file is returned """
        raise NotImplementedError
