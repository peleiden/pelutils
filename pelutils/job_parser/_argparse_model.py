from collections.abc import Iterable, Mapping
from pathlib import Path
from types import NoneType, UnionType
from typing import Annotated, Any, Self, Union, get_args, get_origin  # pyright: ignore[reportDeprecated]

from pydantic import BaseModel, PrivateAttr, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import ErrorDetails
from typing_extensions import override

from ._job_parser import JobParser
from ._structs import ArgumentTypes, Flag, JobDescription, JobParserError, OptionalArg, RequiredArg


def _nargs(field_name: str, annotation: Any) -> int | None:  # pyright: ignore[reportExplicitAny]
    """Return the `nargs` value for a field type, which is None for fields holding one value."""
    if get_origin(annotation) is Annotated:
        return _nargs(field_name, get_args(annotation)[0])

    unsupported = JobParserError(f"Field '{field_name}' has type {annotation}, which cannot be given as command-line values")

    if get_origin(annotation) in (Union, UnionType):  # pyright: ignore[reportDeprecated]
        members = [member for member in get_args(annotation) if member is not NoneType]
        nargs = [_nargs(field_name, member) for member in members]
        if len(members) > 1 and any(n is not None for n in nargs):
            raise unsupported
        return nargs[0]

    origin = get_origin(annotation) or annotation
    if origin is tuple:
        args = get_args(annotation)
        return 0 if not args or args[-1] is Ellipsis else len(args)
    if isinstance(origin, type):
        if issubclass(origin, (Mapping, BaseModel)):
            raise unsupported
        if issubclass(origin, Iterable) and not issubclass(origin, (str, bytes)):
            return 0
    return None


class _FactoryDefault(list[Any]):  # pyright: ignore[reportExplicitAny]
    """Placeholder in job documentation. The parser requires a list of length `nargs` for arguments with `nargs`."""

    @override
    def __repr__(self) -> str:
        return "<default_factory>"


def _argument(field_name: str, field: FieldInfo) -> ArgumentTypes:
    """Convert a model field to an argument. Values stay strings, as they are converted by the model."""
    if field.alias is not None or field.validation_alias is not None:
        raise JobParserError(f"Field '{field_name}' has an alias, which is not supported")
    name = field_name.replace("_", "-")
    description = (field.description or "").replace("%", "%%")

    if field.annotation is bool and field.default is False:
        return Flag(name, help=description)

    nargs = _nargs(field_name, field.annotation)
    if field.is_required():
        return RequiredArg(name, type=str, help=f"{description} (required)", nargs=nargs)

    # Parser defaults are only displayed, so default factories are not called
    default = field.default if field.default_factory is None else _FactoryDefault([None] * (nargs or 0))
    if nargs is not None and default is not None and field.default_factory is None:
        default = list(default)
    if field.default_factory is None:
        description += f" (default: {default})".replace("%", "%%")
    return OptionalArg(name, default=default, type=str, help=description, nargs=nargs)


class ArgparseModel(BaseModel):  # noqa: PLW1641
    """Declare a job's arguments as a typed Pydantic model.

    Subclass it and declare fields, then call :meth:`parse_job` or :meth:`parse_jobs`
    to get instances of the subclass. Values are resolved as in :class:`JobParser`: The
    command line overrides configuration files, which override field defaults.

    Fields map to arguments as follows, where ``learning_rate`` becomes ``--learning-rate``:

    - Fields without a default are required.
    - ``bool`` fields defaulting to ``False`` are flags, which can only be turned on from
      the command line. Other ``bool`` fields take a value, e.g. ``--shuffle false``.
    - ``list``, ``set``, ``Sequence``, and ``tuple[int, ...]`` fields take any number of
      values, while ``tuple[int, float]`` takes exactly two.
    - ``Field(description=...)`` is the help text, and the class docstring is the
      description in ``--help``.
    - Short options are assigned automatically from field names, so they can change when
      fields are added.

    Fields named ``name``, ``config_file``, ``help``, ``explicit_args``, or
    ``docfile_content`` are not allowed. Fields of type ``dict`` or ``BaseModel`` and
    fields with aliases are not supported.

    All values given by the command line or a configuration file are validated by the
    model, so field constraints and validators apply to them. Since those values are
    strings, they are rejected by strict fields and non-string ``Literal`` types (use an
    ``IntEnum`` instead of ``Literal[1, 2]``), and ``int | str`` always results in a string.
    Fields not given a value are left out of ``model_fields_set``.

    Jobs are equal if they have the same type and field values, regardless of their names.
    """

    _job: JobDescription | None = PrivateAttr(default=None)

    @property
    def name(self) -> str:
        """Name of the job, which is the class name if the model was not parsed."""
        return self._job.name if self._job else type(self).__name__

    @classmethod
    def parse_job(cls) -> Self:
        """Parse command-line and configuration input into exactly one job.

        Raises
        ------
        ConfigError
            If the selected configuration resolves to multiple jobs.
        JobParserError
            If a required value is missing, or the model rejects a value.
        """
        return cls._from_job(cls._parser(multiple_jobs=False).parse_job())

    @classmethod
    def parse_jobs(cls) -> list[Self]:
        """Parse command-line and configuration input into one or more jobs.

        Raises
        ------
        JobParserError
            If a required value is missing, or the model rejects a value in any job.
        """
        return [cls._from_job(job) for job in cls._parser(multiple_jobs=True).parse_jobs()]

    def write_documentation(self, path: str | Path, *, append: bool = True):
        """Write the resolved invocation and configuration to ``path``.

        Parent directories are created automatically. Set ``append=False`` to replace
        an existing file; by default, documentation is appended.

        Raises
        ------
        JobParserError
            If the model was not created by :meth:`parse_job` or :meth:`parse_jobs`.
        """
        if self._job is None:
            raise JobParserError("Only parsed jobs can be documented")
        self._job.write_documentation(path, append=append)

    @override
    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return vars(self) == vars(other)

    @classmethod
    def _parser(cls, *, multiple_jobs: bool) -> JobParser:
        cls.model_rebuild()  # Resolve forward references, as field types determine the arguments
        arguments = [_argument(field_name, field) for field_name, field in cls.model_fields.items()]
        return JobParser(*arguments, description=cls.__doc__, multiple_jobs=multiple_jobs)

    @classmethod
    def _from_job(cls, job: JobDescription) -> Self:
        values = {field_name: job[field_name] for field_name in cls.model_fields if field_name in job.explicit_args}
        try:
            model = cls.model_validate(values)
        except ValidationError as e:
            errors = "\n".join(_format_error(error) for error in e.errors())
            raise JobParserError(f"Job '{job.name}' is invalid:\n{errors}") from None
        model._job = job
        return model


def _format_error(error: ErrorDetails) -> str:
    """Describe a validation error by the command-line option that caused it, if any."""
    return f"  --{str(error['loc'][0]).replace('_', '-')}: {error['msg']}" if error["loc"] else f"  {error['msg']}"
