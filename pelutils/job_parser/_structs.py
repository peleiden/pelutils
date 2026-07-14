import re
from abc import ABC
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path
from pprint import pformat
from typing import Any, TypeVar

from typing_extensions import override

_T = TypeVar("_T")
_type = type  # Save `type` under different name to prevent name collisions

# Support for nargs is limited to 0 (any number of args) and set number
# As such, not all modes supported by argparse (see documentation) are supported here
# https://docs.python.org/3/library/argparse.html#nargs
_NargsTypes = int | None


def fixdash(argname: str) -> str:
    """Replace dashes in argument names with underscores."""
    return argname.replace("-", "_")


class JobParserError(Exception):
    """Raised when command-line or configuration input is invalid."""


class ConfigError(JobParserError):
    """Raised when a configuration file cannot be resolved into the requested jobs."""


class _AbstractArgument(ABC):  # noqa: B024
    """Contains description of an argument.

    '--' is automatically prepended to `name` when given from the command line.
    """

    def __init__(self, name: str, abbrev: str | None, help: str | None, **kwargs: Any):  # pyright: ignore[reportExplicitAny]
        self._validate(name, abbrev)

        self.name = name
        self.abbrev = abbrev
        self.help = help
        self.kwargs = kwargs

    @staticmethod
    def _validate(name: str, abbrev: str | None):
        if not name:
            raise ValueError(f"`name` ('{name}') must not be an empty string")
        if name.startswith("-"):
            raise ValueError(f"Double dashes are automatically prepended and should not be given by user: '{name}'")
        if isinstance(abbrev, str) and (len(abbrev) != 1 or not abbrev.isalpha()):
            raise ValueError(f"`abbrev` ('{abbrev}') must be an alpha character and have length 1")
        if re.search(r"\s", name):
            raise ValueError(f"`name` ('{name}') cannot contain whitespace")

    def _name_or_flags(self) -> tuple[str, ...]:
        if self.abbrev:
            return ("-" + self.abbrev, "--" + self.name)
        else:
            return ("--" + self.name,)

    @staticmethod
    def _validate_nargs(nargs: _NargsTypes):
        if type(nargs) not in _NargsTypes.__args__:
            raise TypeError(f"`nargs` type must be one of {_NargsTypes.__args__}, not {type(nargs)}")
        if isinstance(nargs, int) and nargs < 0:
            raise ValueError("When expecting a set number of arguments, the number must be at least 0")

    @override
    def __str__(self) -> str:
        vars_str = ", ".join(f"{name}={value}" for name, value in vars(self).items())
        return f"{self.__class__.__name__}({vars_str})"

    @override
    def __hash__(self) -> int:
        return hash(self.name)


class RequiredArg(_AbstractArgument):
    """Declare a command-line argument which every job must provide.

    Values can be supplied by a command-line option or an INI configuration field.
    The argument is exposed as ``--<name>`` and, when possible, receives an automatic
    single-letter abbreviation.

    Parameters
    ----------
    name : str
        Long option name without leading dashes. Dashes are converted to underscores
        in the resulting :class:`JobDescription` attribute.
    type : Callable[[str], _T], optional
        Function used to convert command-line and configuration values.
    abbrev : str | None, optional
        Optional single-letter short option, without its leading dash.
    help : str | None, optional
        Help text shown by ``--help``.
    metavar : str | tuple[str, ...] | None, optional
        Value label displayed in command-line help.
    nargs : int | None, optional
        Exact number of values required. Set to ``0`` to accept any number of values.
    """

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        *,
        type: Callable[[str], _T] = str,
        abbrev: str | None = None,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
        nargs: _NargsTypes = None,
        **kwargs: Any,  # pyright: ignore[reportExplicitAny]
    ):
        super().__init__(name, abbrev, help=help, **kwargs)
        self._validate_nargs(nargs)
        if "default" in kwargs:
            raise TypeError(f"Class {self.__class__.__name__} does not accept keyword argument 'default'")
        self.type = type
        self.metavar = metavar
        self.nargs = nargs


class OptionalArg(_AbstractArgument):
    """Declare a command-line argument with a default value.

    The value type is inferred from ``default`` when ``type`` is omitted. For list
    values, provide ``nargs`` and ensure every default item has the same type.

    Parameters
    ----------
    name : str
        Long option name without leading dashes.
    default : _T | None, optional
        Value used when the option is absent from both the CLI and configuration.
    type : Callable[[str], _T] | None, optional
        Function used to convert supplied values. Inferred from ``default`` when omitted.
    abbrev : str | None, optional
        Optional single-letter short option, without its leading dash.
    help : str | None, optional
        Help text shown by ``--help``.
    metavar : str | tuple[str, ...] | None, optional
        Value label displayed in command-line help.
    nargs : int | None, optional
        Exact number of values required. Set to ``0`` to accept any number of values.
    """

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        *,
        default: _T | None = None,
        type: Callable[[str], _T] | None = None,
        abbrev: str | None = None,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
        nargs: _NargsTypes = None,
        **kwargs: Any,  # pyright: ignore[reportExplicitAny]
    ):
        super().__init__(name, abbrev, help, **kwargs)
        self._validate_nargs(nargs)

        self.default = default
        if type is not None:
            self.type = type
        elif self.default is not None:
            if nargs is not None:
                self.default = list(self.default)  # pyright: ignore[reportArgumentType]
            self.type = _type(self.default) if nargs is None else _type(self.default[0])  # pyright: ignore[reportIndexIssue]
            if nargs is not None and not all(isinstance(x, self.type) for x in self.default):  # pyright: ignore[reportGeneralTypeIssues]
                raise ValueError(f"All elements in default value of {name} must be of type {self.type}")
        else:
            self.type = str
        self.metavar = metavar
        self.nargs = nargs


class Flag(_AbstractArgument):
    """Declare a boolean command-line flag.

    A flag defaults to ``False`` and becomes ``True`` when supplied on the CLI. INI
    files may use a bare key for ``True`` or an explicit ``True``/``False`` value.

    Parameters
    ----------
    name : str
        Long option name without leading dashes.
    abbrev : str | None, optional
        Optional single-letter short option, without its leading dash.
    help : str | None, optional
        Help text shown by ``--help``.
    """

    def __init__(
        self,
        name: str,
        *,
        abbrev: str | None = None,
        help: str | None = None,
        **kwargs: Any,  # pyright: ignore[reportExplicitAny]
    ):
        super().__init__(name, abbrev, help, **kwargs)

    @property
    def default(self) -> bool:
        """The default value for a Flag is always False."""
        return False


class JobDescription(Namespace):
    """Values resolved for one job by :class:`JobParser`.

    Parsed values are available as attributes and through ``job["option-name"]``;
    dash-separated and underscore-separated keys are interchangeable. ``name`` is
    derived from a configuration section, an explicit ``--name``, or a timestamp.
    ``explicit_args`` records values supplied by the configuration or CLI.
    """

    def __init__(self, name: str, explicit_args: set[str], docfile_content: str, **kwargs: Any):  # pyright: ignore[reportExplicitAny]
        super().__init__(**kwargs)
        self.name = name
        self.explicit_args = explicit_args
        self._docfile_content = docfile_content

    def given_args_to_dict(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Return the resolved public job values as a dictionary.

        Parser bookkeeping and private attributes are not included in the result.
        """
        d = vars(self)
        d = {kw: v for kw, v in d.items() if not kw.startswith("_") and kw not in {"config", "explicit_args"}}
        return d

    def write_documentation(self, path: str | Path, *, append: bool = True):
        """Write the resolved invocation and configuration to ``path``.

        Parent directories are created automatically. Set ``append=False`` to replace
        an existing file; by default, documentation is appended.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a" if append else "w") as docfile:
            docfile.write(self._docfile_content)

    def __getitem__(self, key: str) -> Any:  # pyright: ignore[reportExplicitAny]
        """Get the argument value with the given key. -/_ disambiguities are resolved."""
        if key in self.__dict__:
            return self.__dict__[key]
        elif fixdash(key) in self.__dict__:
            return self.__dict__[fixdash(key)]
        else:
            raise KeyError(f"No such job argument '{key}'")

    @override
    def __str__(self) -> str:
        return pformat(self.given_args_to_dict())


ArgumentTypes = RequiredArg | OptionalArg | Flag
