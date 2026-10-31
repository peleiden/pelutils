import sys
from collections.abc import Sequence
from enum import Enum, IntEnum
from pathlib import Path
from typing import Annotated, Literal, Self

import pytest
from pydantic import Field, model_validator

from pelutils.job_parser import Arg, ArgparseModel, ConfigError, JobParserError
from pelutils.tests import UnitTestCollection, restore_argv


class Color(Enum):
    RED = "red"


class Level(IntEnum):
    LOW = 1


class Job(ArgparseModel):
    """Job description with 100% coverage."""

    data_path: Path = Field(description="Uses 100% of the data")
    learning_rate: float = Field(1e-4, gt=0, description="Step size")
    layers: list[int] = [64, 64]  # noqa: RUF012
    betas: tuple[float, float] = (0.9, 0.999)
    maybe_many: list[int] | None = None
    tags: set[str] = Field(default_factory=set)
    sizes: Sequence[int] = ()
    fp16: bool = False
    shuffle: bool = True
    seed: int | None = None
    color: Color = Color.RED
    level: Level = Level.LOW
    mode: Literal["a", "b"] = "a"

    @model_validator(mode="after")
    def check_learning_rate(self) -> Self:
        if self.learning_rate > 1:
            raise ValueError("Too fast")
        return self


_config = """
[DEFAULT]
data-path = /data
fp16

[first]
learning_rate = 0.1
layers = 1 2 3

[second]
fp16 = False
"""


class Forward(ArgparseModel):
    values: "LateList | None" = None


LateList = list[int]


class TestArgparseModel(UnitTestCollection):
    def setup_class(self):
        super().setup_class()
        self._config_file = self.get_test_path("jobs.ini")
        self._config_file.write_text(_config)

    @staticmethod
    def _parse(*argv: str, model: type[ArgparseModel] = Job):
        sys.argv = ["main.py", *argv]
        return model.parse_job()

    @restore_argv
    def test_defaults(self):
        job = self._parse("--data-path", "x")
        assert isinstance(job, Job)
        assert job.model_dump() == Job(data_path=Path("x")).model_dump()
        assert job.tags == set()
        assert job.model_fields_set == {"data_path"}

    @restore_argv
    def test_conversion(self):
        job = self._parse(
            *"-d x --learning-rate 0.5 --layers 1 2 --betas 0.1 0.2 --maybe-many 7 --tags a b --sizes 3".split(),
            *"--fp16 --shuffle false --seed 2 --color red --level 1 --mode b".split(),
        )
        assert isinstance(job, Job)
        assert job.data_path == Path("x")
        assert job.learning_rate == 0.5
        assert job.layers == [1, 2]
        assert job.betas == (0.1, 0.2)
        assert job.maybe_many == [7]
        assert job.tags == {"a", "b"}
        assert list(job.sizes) == [3]
        assert job.fp16 is True
        assert job.shuffle is False
        assert job.seed == 2
        assert job.color is Color.RED
        assert job.level is Level.LOW
        assert job.mode == "b"

    @restore_argv
    def test_config_precedence(self):
        sys.argv = ["main.py", "-c", f"{self._config_file}:first", "--layers", "9"]
        job = Job.parse_job()
        assert job.name == "first"
        assert job.data_path == Path("/data")  # DEFAULT section
        assert job.learning_rate == 0.1  # Section
        assert job.layers == [9]  # CLI over section
        assert job.shuffle is True  # Field default
        assert job.model_fields_set == {"data_path", "fp16", "learning_rate", "layers"}

        # A flag on the CLI overrides False in the config
        sys.argv = ["main.py", "-c", f"{self._config_file}:second", "--fp16", "--name", "renamed"]
        job = Job.parse_job()
        assert job.name == "renamed"
        assert job.fp16 is True

    @restore_argv
    def test_multiple_jobs(self):
        sys.argv = ["main.py", "-c", str(self._config_file)]
        jobs = Job.parse_jobs()
        assert [job.name for job in jobs] == ["first", "second"]
        assert [job.fp16 for job in jobs] == [True, False]
        assert all(isinstance(job, Job) for job in jobs)
        with pytest.raises(ConfigError):
            Job.parse_job()

    @restore_argv
    def test_invalid_values(self):
        with pytest.raises(JobParserError, match="data-path"):
            self._parse()
        with pytest.raises(JobParserError, match=r"--learning-rate: Input should be greater than 0"):
            self._parse("-d", "x", "--learning-rate", "-1", "--name", "bad-job")
        with pytest.raises(JobParserError, match="bad-job"):
            self._parse("-d", "x", "--learning-rate", "-1", "--name", "bad-job")
        with pytest.raises(JobParserError, match="Too fast"):
            self._parse("-d", "x", "--learning-rate", "2")
        with pytest.raises(JobParserError, match="--layers"):
            self._parse("-d", "x", "--layers", "1", "a")
        with pytest.raises(JobParserError, match="--mode"):
            self._parse("-d", "x", "--mode", "z")
        with pytest.raises(ValueError, match="expected 2 values"):
            self._parse("-d", "x", "--betas", "1")

        # Validation is per section, and the failing section is named
        config = self.get_test_path("invalid.ini")
        config.write_text("[good]\ndata-path = x\n[bad]\ndata-path = x\nlearning-rate = 0\n")
        sys.argv = ["main.py", "-c", str(config)]
        with pytest.raises(JobParserError, match="'bad'"):
            Job.parse_jobs()

    @restore_argv
    def test_required_kinds(self):
        class Required(ArgparseModel):
            items: list[int]
            enabled: bool

        job = self._parse("--items", "1", "2", "--enabled", "true", model=Required)
        assert isinstance(job, Required)
        assert job.items == [1, 2]
        assert job.enabled is True
        with pytest.raises(JobParserError):
            self._parse("--items", "1", model=Required)

    @restore_argv
    def test_unsupported_fields(self):
        class WithDict(ArgparseModel):
            values: dict[str, int] = {}  # noqa: RUF012

        class WithModel(ArgparseModel):
            nested: Job | None = None

        class WithContainerUnion(ArgparseModel):
            values: list[int] | int = 1

        class WithAlias(ArgparseModel):
            value: int = Field(1, alias="other")

        class WithArgDefault(ArgparseModel):
            value: int = Arg(abbrev="v")  # pyright: ignore[reportAssignmentType]

        for model in (WithDict, WithModel, WithContainerUnion, WithAlias, WithArgDefault):
            with pytest.raises(JobParserError, match=r"'(values|nested|value)'"):
                self._parse(model=model)

    @restore_argv
    def test_reserved_names(self):
        class WithConfigFile(ArgparseModel):
            config_file: str = ""

        with pytest.raises(JobParserError, match="reserved"):
            self._parse(model=WithConfigFile)

    @restore_argv
    def test_arg_options(self):
        class WithOptions(ArgparseModel):
            seed: Annotated[int, Arg(abbrev="S")] = 0
            flag: Annotated[bool, Arg(abbrev="F")] = False

        job = self._parse("-S", "3", "-F", model=WithOptions)
        assert isinstance(job, WithOptions)
        assert job.seed == 3
        assert job.flag is True

    @restore_argv
    def test_help(self, capsys: pytest.CaptureFixture[str]):
        with pytest.raises(SystemExit) as e:
            self._parse("--help")
        assert e.value.code == 0
        out = " ".join(capsys.readouterr().out.split())
        assert "Job description with 100% coverage." in out
        assert "Uses 100% of the data (required)" in out
        assert "Step size (default: 0.0001)" in out
        assert "(default: [64, 64])" in out

    @restore_argv
    def test_default_factory_only_called_when_needed(self):
        calls = []

        class WithFactory(ArgparseModel):
            value: int = Field(default_factory=lambda: calls.append(1) or 5)

        job = self._parse("--value", "4", model=WithFactory)
        assert isinstance(job, WithFactory)
        assert job.value == 4
        assert not calls
        assert self._parse(model=WithFactory).value == 5  # pyright: ignore[reportAttributeAccessIssue]
        assert len(calls) == 1

    @restore_argv
    def test_forward_reference(self):
        job = self._parse("--values", "1", "2", model=Forward)
        assert isinstance(job, Forward)
        assert job.values == [1, 2]

    @restore_argv
    def test_annotated_in_union(self):
        class Nested(ArgparseModel):
            values: Annotated[list[int], Field(min_length=1)] | None = None

        job = self._parse("--values", "1", "2", model=Nested)
        assert isinstance(job, Nested)
        assert job.values == [1, 2]

    @restore_argv
    def test_flag_in_config_is_case_insensitive(self):
        class WithFlag(ArgparseModel):
            flag: bool = False

        config = self.get_test_path("flag.ini")
        sys.argv = ["main.py", "-c", str(config)]
        for value, expected in (("true", True), ("True", True), ("FALSE", False)):
            config.write_text(f"[job]\nflag = {value}\n")
            job = WithFlag.parse_job()
            assert isinstance(job, WithFlag)
            assert job.flag is expected
        config.write_text("[job]\nflag = 1\n")
        with pytest.raises(ValueError, match="must be 'True' or 'False'"):
            WithFlag.parse_job()

    @restore_argv
    def test_equality(self):
        first = self._parse("-d", "x", "--name", "first")
        second = self._parse("-d", "x", "--name", "second")
        assert first == second
        assert first == Job(data_path=Path("x"))
        assert first != self._parse("-d", "y")
        assert first != "x"

        class Other(Job):
            pass

        assert Other(data_path=Path("x")) != first

    @restore_argv
    def test_frozen_and_inheritance(self):
        class Frozen(ArgparseModel, frozen=True):
            a: int = 1

        class Child(Frozen):
            b: bool | None = None

        job = self._parse("-a", "2", "-b", "true", model=Child)
        assert isinstance(job, Child)
        assert (job.a, job.b) == (2, True)
        assert hash(job) == hash(Child(a=2, b=True))

    @restore_argv
    def test_name_and_dump(self):
        job = self._parse("-d", "x", "--name", "my-job")
        assert job.name == "my-job"
        assert "name" not in job.model_dump()
        assert set(job.model_dump()) == set(Job.model_fields)

        assert Job(data_path=Path("x")).name == "Job"

    @restore_argv
    def test_documentation(self):
        docfile = self.get_test_path("docs") / "job.ini"
        sys.argv = ["main.py", "-c", f"{self._config_file}:first"]
        job = Job.parse_job()
        job.write_documentation(docfile)
        content = docfile.read_text()
        assert str(self._config_file) in content
        assert "learning_rate = 0.1" in content
        assert "'layers': [64, 64]" in content

        job.write_documentation(docfile, append=False)
        assert docfile.read_text().count("Running job") == 1

        with pytest.raises(JobParserError):
            Job(data_path=Path("x")).write_documentation(docfile)
