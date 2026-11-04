import sys
from collections.abc import Sequence
from enum import Enum, IntEnum
from pathlib import Path
from typing import Annotated, Literal, Self

import pytest
from pydantic import BaseModel, Field, model_validator

from pelutils.job_parser import ArgparseModel, ConfigError, JobParserError
from pelutils.serialization import UniversalJsonModel
from pelutils.tests import UnitTestCollection, restore_argv

JOB_FIELDS = {"name", "documentation"}


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


class ForwardInner(BaseModel):
    nested: "LateModel | None" = None
    values: "LateList" = []


class ForwardOuter(ArgparseModel):
    inner: ForwardInner = Field(default_factory=ForwardInner)


class LateModel(BaseModel):
    k: int = 0


LateList = list[int]


class Schedule(BaseModel):
    warmup: int
    decay: float = 0.5


class Optimizer(BaseModel):
    learning_rate: float = Field(1e-3, gt=0)
    momentum: float = 0.9
    nesterov: bool = False
    schedule: Schedule = Schedule(warmup=10)
    steps: int = Field(default=0, init=False)


class Data(BaseModel):
    path: Path
    workers: int = 1


class Train(ArgparseModel):
    data: Data
    optimizer: Optimizer = Optimizer(momentum=0.5)
    schedule: Schedule | None = None
    epochs: int = 10
    run_id: str = Field(default="", init=False)


class JsonTrain(ArgparseModel, UniversalJsonModel):
    data: Data
    optimizer: Optimizer = Optimizer(momentum=0.5)


class JsonTrainReversed(UniversalJsonModel, ArgparseModel):
    data: Data


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
        assert job == Job(data_path=Path("x"))
        assert job.tags == set()
        assert job.model_fields_set == {"data_path", *JOB_FIELDS}

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
        assert job.model_fields_set == {"data_path", "fp16", "learning_rate", "layers", *JOB_FIELDS}

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

        class WithModels(ArgparseModel):
            nested: list[Job] = []  # noqa: RUF012

        class WithModelUnion(ArgparseModel):
            nested: Job | int = 1

        class WithContainerUnion(ArgparseModel):
            values: list[int] | int = 1

        class WithAlias(ArgparseModel):
            value: int = Field(1, alias="other")

        for model in (WithDict, WithModels, WithModelUnion, WithContainerUnion, WithAlias):
            with pytest.raises(JobParserError, match=r"'(values|nested|value)'"):
                self._parse(model=model)

    @restore_argv
    def test_reserved_names(self):
        class WithConfigFile(ArgparseModel):
            config_file: str = ""

        with pytest.raises(JobParserError, match="reserved"):
            self._parse(model=WithConfigFile)

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
        assert job.model_dump()["name"] == "my-job"
        assert "Running job" in job.model_dump()["documentation"]
        assert "documentation" not in repr(job)

        unparsed = Job(data_path=Path("x"))
        assert unparsed.name == ""
        assert unparsed.documentation is None

    @restore_argv
    def test_documentation_of_default_factory(self):
        class WithFactory(ArgparseModel):
            one: int = Field(default_factory=lambda: 1)
            many: list[int] = Field(default_factory=lambda: [1, 2])
            pair: tuple[int, float] = Field(default_factory=lambda: (1, 2.0))

        docfile = self.get_test_path("docs") / "factory.ini"
        job = self._parse(model=WithFactory)
        job.write_documentation(docfile, append=False)
        content = docfile.read_text()
        assert "'one': <default_factory>" in content
        assert "'many': <default_factory>" in content
        assert "'pair': <default_factory>" in content
        assert job.model_dump(exclude=JOB_FIELDS) == {"one": 1, "many": [1, 2], "pair": (1, 2.0)}

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

    @restore_argv
    def test_nested(self):
        job = self._parse(
            *"--data.path /d --optimizer.learning-rate 0.1 --optimizer.nesterov --optimizer.schedule.decay 0.2".split(),
            model=Train,
        )
        assert isinstance(job, Train)
        assert job.data == Data(path=Path("/d"))
        # Values not given keep the default instance's, including in nested models
        assert job.optimizer == Optimizer(learning_rate=0.1, momentum=0.5, nesterov=True, schedule=Schedule(warmup=10, decay=0.2))
        assert job.optimizer.model_fields_set == {"learning_rate", "momentum", "nesterov", "schedule"}
        assert job.optimizer.schedule.model_fields_set == {"warmup", "decay"}
        assert job.schedule is None
        assert job.model_fields_set == {"data", "optimizer", *JOB_FIELDS}

        # Unused models with defaults are left to Pydantic
        job = self._parse("--data.path", "/d", model=Train)
        assert isinstance(job, Train)
        assert job.optimizer == Optimizer(momentum=0.5)
        assert job.data.model_fields_set == {"path"}
        assert job.model_fields_set == {"data", *JOB_FIELDS}

    @restore_argv
    def test_nested_config(self):
        config = self.get_test_path("nested.ini")
        config.write_text("[job]\ndata.path = /d\noptimizer.momentum = 0.1\noptimizer.nesterov\nschedule.warmup = 3\n")
        sys.argv = ["main.py", "-c", str(config), "--optimizer.momentum", "0.2"]
        job = Train.parse_job()
        assert job.data.path == Path("/d")
        assert job.optimizer == Optimizer(momentum=0.2, nesterov=True)
        assert job.schedule == Schedule(warmup=3)

    @restore_argv
    def test_nested_default_factory(self):
        class WithFactory(ArgparseModel):
            optimizer: Optimizer = Field(default_factory=lambda: Optimizer(momentum=0.5))

        job = self._parse("--optimizer.learning-rate", "0.1", model=WithFactory)
        assert isinstance(job, WithFactory)
        assert job.optimizer == Optimizer(learning_rate=0.1, momentum=0.5)

        class TakesData(ArgparseModel):
            optimizer: Optimizer = Field(default_factory=lambda _data: Optimizer())  # pyright: ignore[reportUnknownLambdaType]

        with pytest.raises(JobParserError, match="default of field 'optimizer'"):
            self._parse(model=TakesData)

    @restore_argv
    def test_nested_defaults_are_not_shared(self):
        class WithList(BaseModel):
            values: list[int] = [1]

        class Shared(ArgparseModel):
            nested: WithList = WithList(values=[2])
            other: int = 0

        sys.argv = ["main.py", "--other", "1"]
        first, second = Shared.parse_job(), Shared.parse_job()
        first.nested.values.append(3)
        assert second.nested.values == [2]

    @restore_argv
    def test_optional_model(self):
        job = self._parse("--data.path", "/d", "--schedule.warmup", "5", model=Train)
        assert isinstance(job, Train)
        assert job.schedule == Schedule(warmup=5)
        with pytest.raises(JobParserError, match=r"--schedule\.warmup: Field required"):
            self._parse("--data.path", "/d", "--schedule.decay", "0.1", model=Train)
        with pytest.raises(JobParserError, match=r"--optimizer\.learning-rate: Input should be greater than 0"):
            self._parse("--data.path", "/d", "--optimizer.learning-rate", "0", model=Train)
        with pytest.raises(JobParserError, match=r"Missing value for 'data\.path'"):
            self._parse(model=Train)

        class WithDefault(ArgparseModel):
            schedule: Schedule | None = Schedule(warmup=1)

        class Required(ArgparseModel):
            schedule: Schedule | None

        for model in (WithDefault, Required):
            with pytest.raises(JobParserError, match="'schedule' is an optional model, so its default must be None"):
                self._parse(model=model)

    @restore_argv
    def test_nested_default_subclass(self):
        class SubSchedule(Schedule):
            extra: int = 0

        class WithSubclass(ArgparseModel):
            schedule: Schedule = SubSchedule(warmup=1)

        with pytest.raises(JobParserError, match="default of type SubSchedule, which must be Schedule"):
            self._parse(model=WithSubclass)

    @restore_argv
    def test_init_false(self):
        for argv in (("--run-id", "x"), ("--steps", "1"), ("--optimizer.steps", "1")):
            with pytest.raises(SystemExit):
                self._parse("--data.path", "/d", *argv, model=Train)
        config = self.get_test_path("init.ini")
        config.write_text("[job]\ndata.path = /d\noptimizer.steps = 1\n")
        sys.argv = ["main.py", "-c", str(config)]
        with pytest.raises(JobParserError, match=r"Unknown argument 'optimizer\.steps'"):
            Train.parse_job()

        class NoDefault(BaseModel):
            steps: int = Field(init=False)

        class WithNoDefault(ArgparseModel):
            nested: NoDefault

        with pytest.raises(JobParserError, match=r"'nested\.steps' has init=False but no default"):
            self._parse(model=WithNoDefault)

        class WholeModel(ArgparseModel):
            data: Data = Field(default=Data(path=Path("/d")), init=False)
            value: int = 0

        job = self._parse("--value", "1", model=WholeModel)
        assert isinstance(job, WholeModel)
        assert job.data == Data(path=Path("/d"))
        with pytest.raises(SystemExit):
            self._parse("--data.path", "/x", model=WholeModel)

    @restore_argv
    def test_nested_short_options(self, capsys: pytest.CaptureFixture[str]):
        class Short(ArgparseModel):
            data: Data
            delay: int = 0

        job = self._parse("--data.path", "/d", "-d", "2", model=Short)
        assert isinstance(job, Short)
        assert job.delay == 2
        with pytest.raises(SystemExit):
            self._parse("--help", model=Short)
        out = capsys.readouterr().out
        assert "--data.path DATA.PATH" in out
        assert "-D" not in out

    @restore_argv
    def test_job_fields(self):
        # name and documentation are not arguments and do not affect equality or hashing
        with pytest.raises(SystemExit):
            self._parse("-d", "x", "--documentation", "y")

        class Frozen(ArgparseModel, frozen=True):
            a: int = 1

        first = self._parse("--name", "first", model=Frozen)
        second = self._parse("--name", "second", model=Frozen)
        assert first == second
        assert hash(first) == hash(second)
        with pytest.raises(TypeError, match="unhashable"):
            hash(self._parse("-d", "x"))

        for name in ("name", "documentation"):
            redefined = type("Redefined", (ArgparseModel,), {"__annotations__": {name: str}, name: ""})
            with pytest.raises(JobParserError, match=f"'{name}' is reserved"):
                self._parse(model=redefined)

    @restore_argv
    def test_universal_json_model(self):
        path = self.get_test_path("json") / "job.json"
        sys.argv = ["main.py", "--data.path", "/d", "--optimizer.learning-rate", "0.1", "--name", "run"]
        job = JsonTrain.parse_job()
        job.save(path)
        loaded = JsonTrain.load(path)
        assert loaded == job
        assert loaded.optimizer == Optimizer(learning_rate=0.1, momentum=0.5)
        assert loaded.name == "run"
        docfile = self.get_test_path("json") / "job.ini"
        loaded.write_documentation(docfile)
        assert "--optimizer.learning-rate 0.1" in docfile.read_text()

        sys.argv = ["main.py", "--data.path", "/d"]
        job = JsonTrainReversed.parse_job()
        job.save(path)
        assert JsonTrainReversed.load(path) == job

    @restore_argv
    def test_nested_forward_reference(self):
        job = self._parse("--inner.nested.k", "1", "--inner.values", "2", "3", model=ForwardOuter)
        assert isinstance(job, ForwardOuter)
        assert job.inner == ForwardInner(nested=LateModel(k=1), values=[2, 3])

    @restore_argv
    def test_required_model_with_defaults(self):
        class WithRequired(ArgparseModel):
            data: Data = Data(path=Path("/d"))
            optimizer: Optimizer
            optional: Optimizer | None = None

        job = self._parse(model=WithRequired)
        assert isinstance(job, WithRequired)
        assert job.optimizer == Optimizer()
        assert job.optional is None
        # A required model inside a given optional model is built from its defaults as well
        job = self._parse("--optional.learning-rate", "0.1", model=WithRequired)
        assert isinstance(job, WithRequired)
        assert job.optional == Optimizer(learning_rate=0.1)

    @restore_argv
    def test_model_validator_error(self):
        class Limited(BaseModel):
            low: int = 0
            high: int = 1

            @model_validator(mode="after")
            def check(self) -> Self:
                if self.low > self.high:
                    raise ValueError("low above high")
                return self

        class WithLimited(ArgparseModel):
            limits: Limited = Limited()

        with pytest.raises(JobParserError, match=r"\n  limits: Value error, low above high"):
            self._parse("--limits.low", "2", model=WithLimited)

    @restore_argv
    def test_edge_underscores(self):
        class Inner(BaseModel):
            beta_: int = 0

        class Edges(ArgparseModel):
            lambda_: float = 0.0
            max__norm__: int = 0
            inner: Inner = Inner()

        job = self._parse(*"--lambda_ 0.5 --max--norm__ 2 --inner.beta_ 3".split(), model=Edges)
        assert job == Edges(lambda_=0.5, max__norm__=2, inner=Inner(beta_=3), name=job.name)

        with pytest.raises(JobParserError, match=r"\n  --inner\.beta_: "):
            self._parse("--inner.beta_", "x", model=Edges)

    @restore_argv
    def test_invalid_model_defaults(self):
        class DictDefault(ArgparseModel):
            schedule: Schedule = Field({"warmup": 1}, validate_default=True)  # pyright: ignore[reportAssignmentType]

        with pytest.raises(JobParserError, match="default of type dict, which must be Schedule"):
            self._parse(model=DictDefault)

        class Generated(ArgparseModel, alias_generator=str.upper):
            value: int = 0

        with pytest.raises(JobParserError, match="alias_generator"):
            self._parse(model=Generated)
