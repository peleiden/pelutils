from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from types import NoneType, UnionType
from typing import Annotated, Any, Self, Union, get_args, get_origin  # pyright: ignore[reportDeprecated]

from pydantic import BaseModel, Field, ValidationError
from pydantic.fields import FieldInfo
from pydantic_core import ErrorDetails, PydanticUndefined
from typing_extensions import override

from pelutils.misc import except_keys

from ._job_parser import JobParser
from ._structs import ArgumentTypes, Flag, JobDescription, JobParserError, OptionalArg, RequiredArg

# Fields declared by ArgparseModel to describe how a job was parsed rather than what it does
_JOB_FIELDS = ("name", "documentation")
# Marks a field whose default comes from a default factory, which is not called to build the parser
_FACTORY = object()


def _unwrap(annotation: Any) -> Any:  # pyright: ignore[reportExplicitAny]
    """Remove ``Annotated`` wrappers, which Pydantic only strips at the top level of a field."""
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return annotation


def _is_model(annotation: Any) -> bool:  # pyright: ignore[reportExplicitAny]
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def _model_class(field: FieldInfo) -> type[BaseModel] | None:
    """Return the model class of a ``Model`` or ``Model | None`` field, or None for other fields."""
    annotation = _unwrap(field.annotation)
    if get_origin(annotation) in (Union, UnionType):  # pyright: ignore[reportDeprecated]
        members = [_unwrap(member) for member in get_args(annotation) if member is not NoneType]
        # Unions of a model with other types are not models, so _nargs rejects them
        annotation = members[0] if len(members) == 1 else None
    return annotation if _is_model(annotation) else None


def _nargs(field_name: str, annotation: Any) -> int | None:  # pyright: ignore[reportExplicitAny]
    """Return the `nargs` value for a field type, which is None for fields holding one value."""
    annotation = _unwrap(annotation)
    unsupported = JobParserError(f"Field '{field_name}' has type {annotation}, which cannot be given as command-line values")

    if get_origin(annotation) in (Union, UnionType):  # pyright: ignore[reportDeprecated]
        members = [member for member in get_args(annotation) if member is not NoneType]
        nargs = [_nargs(field_name, member) for member in members]
        if len(members) > 1 and any(n is not None for n in nargs):
            raise unsupported
        return nargs[0]

    origin = get_origin(annotation) or annotation
    if isinstance(origin, type) and issubclass(origin, (Mapping, BaseModel)):
        raise unsupported
    # Container elements are given as strings, so they cannot be models or mappings either
    for element in get_args(annotation):
        element = get_origin(_unwrap(element)) or _unwrap(element)  # noqa: PLW2901
        if isinstance(element, type) and issubclass(element, (Mapping, BaseModel)):
            raise unsupported
    if origin is tuple:
        args = get_args(annotation)
        return 0 if not args or args[-1] is Ellipsis else len(args)
    if isinstance(origin, type) and issubclass(origin, Iterable) and not issubclass(origin, (str, bytes)):
        return 0
    return None


def _model_default(name: str, field: FieldInfo) -> Any:  # pyright: ignore[reportExplicitAny]
    """Return a model field's default, calling its default factory, as nested defaults depend on it."""
    try:
        # Pydantic copies the default, so jobs do not share mutable values
        return field.get_default(call_default_factory=True)
    except ValueError as e:  # Includes factories that require validated data and invalid models
        raise JobParserError(f"Unable to get the default of field '{name}': {e}") from e


def _field_default(name: str, field: FieldInfo, parent: Any) -> Any:  # pyright: ignore[reportExplicitAny]
    """Return the default of a field in a model whose own default is `parent`.

    `parent` is a model instance if the model has a default, None if the model is optional
    and defaults to None, and PydanticUndefined if the model is required. Defaults of the
    instance take precedence over the field's, so ``Optimizer(momentum=0.5)`` is respected.
    Fields required in an optional model default to None, as they are only needed if the
    model is given. Model fields return their default instance, and other fields with a
    default factory return `_FACTORY`.
    """
    if isinstance(parent, BaseModel):
        return getattr(parent, name.rsplit(".", 1)[-1])
    if field.is_required():
        return parent
    if _model_class(field) is not None:
        return _model_default(name, field)
    return _FACTORY if field.default_factory is not None else field.default


def _leaves(model: type[BaseModel], prefix: str = "", parent: Any = PydanticUndefined) -> Iterator[tuple[str, FieldInfo, Any]]:  # pyright: ignore[reportExplicitAny]
    """Yield the dotted name, field, and default of each argument, recursing into model fields."""
    for field_name, field in model.model_fields.items():
        name = prefix + field_name
        # Aliases would change the keys used to validate and overlay values, including for init=False fields
        if field.alias is not None or field.validation_alias is not None:
            raise JobParserError(f"Field '{name}' has an alias, which is not supported, including from an alias_generator")
        # Pydantic ignores init on models, so it only marks fields to leave out of the parser
        if field.init is False:
            # Such a field is not an argument, so a parse would always fail with an error for an unknown option
            if field.is_required():
                raise JobParserError(f"Field '{name}' has init=False but no default, so it can never be set")
            continue

        default = _field_default(name, field, parent)
        nested = _model_class(field)
        if nested is None:
            yield name, field, default
            continue
        # An optional model is None unless its arguments are given, which only fits a default of None
        if field.annotation is not nested and (field.default is not None or field.default_factory is not None):
            raise JobParserError(f"Field '{name}' is an optional model, so its default must be None")
        # Partially given models are overlaid on an instance of the annotated model, so other defaults such as
        # dicts or subclass instances would be lost
        if default is not PydanticUndefined and default is not None and type(default) is not nested:
            raise JobParserError(f"Field '{name}' has a default of type {type(default).__name__}, which must be {nested.__name__}")
        # Forward references in nested models are only resolved when they are rebuilt
        nested.model_rebuild()
        yield from _leaves(nested, f"{name}.", default)


class _FactoryDefault(list[Any]):  # pyright: ignore[reportExplicitAny]
    """Placeholder in job documentation. The parser requires a list of length `nargs` for arguments with `nargs`."""

    @override
    def __repr__(self) -> str:
        return "<default_factory>"


def _argument(name: str, field: FieldInfo, default: Any) -> ArgumentTypes:  # pyright: ignore[reportExplicitAny]
    """Convert a field to an argument. Values stay strings, as they are converted by the model."""
    arg_name = name.replace("_", "-")
    description = (field.description or "").replace("%", "%%")

    if field.annotation is bool and default is False:
        return Flag(arg_name, help=description)

    nargs = _nargs(name, field.annotation)
    if default is PydanticUndefined:
        return RequiredArg(arg_name, type=str, help=f"{description} (required)", nargs=nargs)

    # Parser defaults are only displayed, so default factories are not called
    if default is _FACTORY:
        default = _FactoryDefault([None] * (nargs or 0))
    else:
        if nargs is not None and default is not None:
            default = list(default)
        description += f" (default: {default})".replace("%", "%%")
    return OptionalArg(arg_name, default=default, type=str, help=description, nargs=nargs)


def _overlay(model: type[BaseModel], values: dict[str, Any], parent: Any) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Add defaults to the values of nested models that were partially given.

    Validating ``{"momentum": 0.5}`` as a model would use the class defaults for the other
    fields, discarding a default instance such as ``Optimizer(learning_rate=0.1)``. `parent`
    is as in :func:`_field_default`. The default's values are validated again, which matters
    only for validators that are not idempotent.
    """
    for field_name, field in model.model_fields.items():
        nested = _model_class(field)
        # Required models are built even if none of their arguments are given, so their fields can all have defaults.
        # Missing required arguments are reported by the parser, and models in a default instance come from it
        if nested is not None and (field_name in values or (field.is_required() and not isinstance(parent, BaseModel))):
            values[field_name] = _overlay(nested, values.get(field_name, {}), _field_default(field_name, field, parent))
    if isinstance(parent, BaseModel):
        # Only set fields are copied, so model_fields_set of the result matches that of the default
        values = {name: getattr(parent, name) for name in parent.model_fields_set} | values
    return values


class ArgparseModel(BaseModel):
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
    - Fields of a ``BaseModel`` type are argument groups, where ``optimizer.learning_rate``
      becomes ``--optimizer.learning-rate``. Partially given models keep the remaining values
      of the default, which may be an instance or a default factory. A model field without a
      default is required, but its fields may have defaults. ``Model | None = None`` fields
      are None unless one of their arguments is given.
    - Fields with ``Field(init=False)`` are not arguments and must have a default.
    - ``Field(description=...)`` is the help text, and the class docstring is the
      description in ``--help``.
    - Short options are assigned automatically from field names, so they can change when
      fields are added. Fields of nested models have no short options.

    Fields named ``config_file``, ``help``, ``explicit_args``, or ``docfile_content`` are not
    allowed, and ``name`` and ``documentation`` are declared by this class. Fields of type
    ``dict``, containers of models, unions of models with other types, and fields with aliases
    are not supported.

    All values given by the command line or a configuration file are validated by the
    model, so field constraints and validators apply to them. Since those values are
    strings, they are rejected by strict fields and non-string ``Literal`` types (use an
    ``IntEnum`` instead of ``Literal[1, 2]``), and ``int | str`` always results in a string.
    Values kept from a nested default are validated again. Fields not given a value are left out of
    ``model_fields_set``, except ``name`` and ``documentation``, which are set by parsing.

    Pydantic does not enforce ``init=False`` on models, so such fields can still be given to the
    constructor; only type checkers reject them.

    Jobs are equal if they have the same type and field values, regardless of their
    ``name`` and ``documentation``.

    To save and load jobs as JSON, also inherit from
    :class:`~pelutils.serialization.UniversalJsonModel`, e.g.
    ``class TrainJob(ArgparseModel, UniversalJsonModel)``. Loaded jobs keep their ``name``
    and can still be documented with :meth:`write_documentation`.
    """

    name: str = Field(default="", init=False, description="Name of the job, which is empty if the model was not parsed")
    documentation: str | None = Field(
        default=None,
        init=False,
        repr=False,
        description="Invocation and configuration of a parsed job, as written by write_documentation",
    )

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
        parser, names = cls._parser(multiple_jobs=False)
        return cls._from_job(parser.parse_job(), names)

    @classmethod
    def parse_jobs(cls) -> list[Self]:
        """Parse command-line and configuration input into one or more jobs.

        Raises
        ------
        JobParserError
            If a required value is missing, or the model rejects a value in any job.
        """
        parser, names = cls._parser(multiple_jobs=True)
        return [cls._from_job(job, names) for job in parser.parse_jobs()]

    def write_documentation(self, path: str | Path, *, append: bool = True):
        """Write the resolved invocation and configuration to ``path``.

        Parent directories are created automatically. Set ``append=False`` to replace
        an existing file; by default, documentation is appended.

        Raises
        ------
        JobParserError
            If the model was not created by :meth:`parse_job` or :meth:`parse_jobs`.
        """
        if self.documentation is None:
            raise JobParserError("Only parsed jobs can be documented")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a" if append else "w") as docfile:
            docfile.write(self.documentation)

    @override
    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return except_keys(vars(self), _JOB_FIELDS) == except_keys(vars(other), _JOB_FIELDS)

    @override
    def __hash__(self) -> int:
        # Pydantic generates a hash of all fields for frozen subclasses unless a base class defines one,
        # which would make equal jobs with different names hash differently
        if not self.model_config.get("frozen"):
            raise TypeError(f"unhashable type: '{type(self).__name__}'")
        return hash((type(self), *except_keys(vars(self), _JOB_FIELDS).values()))

    @classmethod
    def _parser(cls, *, multiple_jobs: bool) -> tuple[JobParser, Sequence[str]]:
        """Return the job parser and the dotted names of its arguments."""
        cls.model_rebuild()  # Resolve forward references, as field types determine the arguments
        for name in _JOB_FIELDS:
            # Without init=False, a redefinition would become an argument and conflict with the job's own values
            if cls.model_fields[name].init is not False:
                raise JobParserError(f"Field '{name}' is reserved by ArgparseModel and cannot be redefined")
        leaves = list(_leaves(cls))
        arguments = [_argument(*leaf) for leaf in leaves]
        for argument in arguments:
            # The first letter of a nested argument names its group rather than the argument,
            # and assigning one would take letters from later top-level arguments
            argument._auto_abbrev = "." not in argument.name  # pyright: ignore[reportPrivateUsage]
        return JobParser(*arguments, description=cls.__doc__, multiple_jobs=multiple_jobs), [name for name, _, _ in leaves]

    @classmethod
    def _from_job(cls, job: JobDescription, names: Sequence[str]) -> Self:
        # Only explicit values are validated, so Pydantic applies defaults and tracks model_fields_set
        values: dict[str, Any] = {}  # pyright: ignore[reportExplicitAny]
        for name in names:
            if name in job.explicit_args:
                *path, field_name = name.split(".")
                target = values
                for part in path:
                    target = target.setdefault(part, {})
                target[field_name] = job[name]
        values = _overlay(cls, values, PydanticUndefined)
        values |= {"name": job.name, "documentation": job._docfile_content}  # pyright: ignore[reportPrivateUsage]

        try:
            return cls.model_validate(values)
        except ValidationError as e:
            errors = "\n".join(_format_error(cls, error) for error in e.errors())
            raise JobParserError(f"Job '{job.name}' is invalid:\n{errors}") from None


def _format_error(model: type[BaseModel], error: ErrorDetails) -> str:
    """Describe a validation error by the command-line option that caused it, if any."""
    # The location continues past the option with e.g. list indices, which are left out
    path: list[str] = []
    nested: type[BaseModel] | None = model
    for part in error["loc"]:
        if nested is None or not isinstance(part, str) or part not in nested.model_fields:
            break
        path.append(part)
        nested = _model_class(nested.model_fields[part])
    if not path:
        return f"  {error['msg']}"
    # Errors of a whole nested model, e.g. from its model validators, have no option of their own
    location = ".".join(path).replace("_", "-")
    return f"  {location}: {error['msg']}" if nested is not None else f"  --{location}: {error['msg']}"
