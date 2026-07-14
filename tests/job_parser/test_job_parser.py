import itertools
import shlex
import sys
from pathlib import Path

import pytest

from pelutils.job_parser import ConfigError, Flag, JobDescription, JobParser, JobParserError, OptionalArg, RequiredArg
from pelutils.job_parser._structs import fixdash
from pelutils.misc import except_keys
from pelutils.tests import UnitTestCollection, restore_argv

_testdir = "parser_test"
_argv_template = ["main.py"]
_sample_argv = f"{_argv_template[0]} -g 4 --gib-num 3.2 -o 7 -i -a b c".split()


def _sample_argv_conf(config_path_str: str | Path) -> list[str]:
    return (f"{_argv_template[0]} -c {config_path_str} --gib-num 3.2").split()


_sample_arguments = [
    RequiredArg("gibstr"),
    RequiredArg("gib-num", type=float),
    RequiredArg("arg-two", nargs=2),
    OptionalArg("opt-int", default=4),
    OptionalArg("opt-d", abbrev="o", default=6, type=lambda x: 2 * int(x)),
    OptionalArg("opt-many", nargs=0, default=list(), type=float),
    OptionalArg("opt-default-none", nargs=2, default=None, type=int),
    OptionalArg("hello", default="there"),
    OptionalArg("Cased-Option", default="Kebab-Pascal"),
    Flag("iam-bool", abbrev="i"),
    Flag("Cased-Flag"),
]

_sample_no_default = """
[IAMNOTDEFAULT]
gibstr=not default
arg-two=1 2
opt-default-none=2 3
"""
_sample_default_only = """
[DEFAULT]
gibstr=pistaccio
arg-two=1 2
Cased-Option=Pascal-Kebab
iam-bool
Cased-Flag
"""
_sample_single_section = (
    _sample_default_only
    + """
[BUTWHATABOUTSECONDJOB]
iam-bool=False
gib-num=5
"""
)
_sample_multiple_section = (
    _sample_single_section
    + """
[THETHIRDJOB]
gibstr=but they were all of them deceived, for another job was made
opt-d=8
opt-int=5
iam-bool=True
arg-two=1 3
opt-many=1 4.5 -3
"""
)
_sample_single_nargs = """
[DEFAULT]
foo=3 4
"""


class TestParser(UnitTestCollection):
    def setup_class(self):
        super().setup_class()
        self._no_default_file = self.get_test_path("no-default.ini")
        self._default_file = self.get_test_path("default-only.ini")
        self._single_job_file = self.get_test_path("single-job.ini")
        self._multiple_jobs_file = self.get_test_path("multiple-jobs.ini")
        self._sample_single_nargs_file = self.get_test_path("single-nargs.ini")
        with open(self._no_default_file, "w") as f:
            f.write(_sample_no_default)
        with open(self._default_file, "w") as f:
            f.write(_sample_default_only)
        with open(self._single_job_file, "w") as f:
            f.write(_sample_single_section)
        with open(self._multiple_jobs_file, "w") as f:
            f.write(_sample_multiple_section)
        with open(self._sample_single_nargs_file, "w") as f:
            f.write(_sample_single_nargs)

    def test_argument_validation(self):
        with pytest.raises(ValueError):
            RequiredArg("")
        with pytest.raises(ValueError):
            OptionalArg("--Hello there", default="General Kenobi")
        with pytest.raises(ValueError):
            Flag("show-memes", abbrev="sm")
        with pytest.raises(ValueError):
            OptionalArg("memes", abbrev="-s", default="doge")
        with pytest.raises(ValueError):
            Flag("-show-memes")
        for char in (" ", "\t", "\n"):
            with pytest.raises(ValueError):
                RequiredArg(f"hello{char}there")
        with pytest.raises(TypeError):
            RequiredArg("default", default=4)
        with pytest.raises(TypeError):
            RequiredArg("multiple-args", nargs="?")
        with pytest.raises(ValueError):
            OptionalArg("no-args", nargs=-1, default=[])
        RequiredArg("meme-folder")
        OptionalArg("memes", abbrev="m", default="doge")
        Flag("show-memes", abbrev="s")

    def test_job_description(self):
        j = JobDescription(
            name="groot",
            explicit_args=set(),
            docfile_content="",
            a=2,
            a_b=4,
        )
        assert j.name == j["name"]
        assert j.a == j["a"]
        assert j.a_b == j["a_b"]
        assert j.a_b == j["a-b"]
        with pytest.raises(KeyError):
            j["ab"]
        with pytest.raises(AttributeError):
            j.ab  # noqa: B018

        job_dict = j.given_args_to_dict()
        for kw, v in job_dict.items():
            assert getattr(j, kw) == v
            assert not kw.startswith("_")
            assert kw != "explicit_args"

    @restore_argv
    def test_job_description_format(self):
        sys.argv = _sample_argv
        parser = JobParser(*_sample_arguments)

        job = parser.parse_job()
        for arg in _sample_arguments:
            assert fixdash(arg.name) in str(job)

    def test_argument_format(self):
        for arg in _sample_arguments:
            assert arg.name in str(arg)
            assert arg.__class__.__name__ in str(arg)

    def test_argument_hash(self):
        assert hash(RequiredArg("name")) == hash(OptionalArg("name")) == hash(Flag("name"))
        assert hash(RequiredArg("name")) != hash(OptionalArg("namer")) != hash(Flag("namerr"))

    @restore_argv
    def test_name_and_abbreviation_handling(self):
        """Test that name abbreviation ordering and collisions are handled properly"""
        with pytest.raises(JobParserError):
            JobParser(RequiredArg("arg1", abbrev="a"), RequiredArg("arg2", abbrev="a"))
        with pytest.raises(JobParserError):
            JobParser(RequiredArg("help"))

        # Test that under no permutations is the ordering changed in the argparser
        sys.argv = _argv_template
        sample_args = [
            OptionalArg("quick-mafs", default=0),
            Flag("Quick-flag", abbrev="Q"),
            OptionalArg("quick-boi", abbrev="q", default=1),
        ]
        for ordering in itertools.permutations(range(len(sample_args))):
            p = JobParser(*(sample_args[i] for i in ordering))
            args = p._argparser.parse_args()
            for i, (argname, value) in enumerate(except_keys(vars(args), [fixdash(x) for x in JobParser._reserved_names]).items()):
                arg = sample_args[ordering[i]]
                assert fixdash(arg.name) == argname
                assert arg.default == value

        # Test naming conflicts
        with pytest.raises(JobParserError):
            JobParser(RequiredArg("a-b"), Flag("a_b"))

    def test_parser_properties(self):
        assert JobParser().reserved_names == {"config-file", "name", "help"}
        assert JobParser().reserved_abbreviations == {"c"}

    @restore_argv
    def test_no_conf_single_job(self):
        sys.argv = _sample_argv
        parser = JobParser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_job()

        assert isinstance(job, JobDescription)
        assert job.gibstr == "4"
        assert job.gib_num == float("3.2")
        assert job.arg_two == ["b", "c"]
        assert job.opt_int == 4
        assert job.opt_d == 14
        assert job.opt_many == list()
        assert job.opt_default_none is None
        assert job.iam_bool
        assert job.explicit_args == {"gibstr", "gib_num", "arg_two", "opt_d", "iam_bool"}

    @restore_argv
    def test_conf_single_job(self):
        # Test with only default section
        sys.argv = _sample_argv_conf(self._single_job_file)
        parser = JobParser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_job()

        assert job.name == "BUTWHATABOUTSECONDJOB"
        assert job.gibstr == "pistaccio"
        assert job.gib_num == float("3.2")
        assert job.opt_int == 4
        assert job.opt_d == 6
        assert not job.iam_bool

        # Test that multiple sections throws an error, unless DEFAULT is one of only two sections
        sys.argv = _sample_argv_conf(self._single_job_file)
        parser = JobParser(*_sample_arguments, multiple_jobs=False)
        parser.parse_job()

        sys.argv = _sample_argv_conf(self._multiple_jobs_file)
        parser = JobParser(*_sample_arguments, multiple_jobs=False)
        with pytest.raises(ConfigError):
            parser.parse_job()

    @restore_argv
    def test_no_conf_multiple_jobs(self):
        sys.argv = [*_sample_argv, "--name", "good-name"]
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_jobs()
        assert len(jobs) == 1
        job = jobs[0]

        assert job.name == "good-name"
        assert job.gibstr == "4"
        assert job.gib_num == float("3.2")
        assert job.arg_two == ["b", "c"]
        assert job.opt_int == 4
        assert job.opt_d == 14
        assert job.opt_many == list()
        assert job.iam_bool

    @restore_argv
    def test_conf_multiple_jobs(self):
        sys.argv = _sample_argv_conf(self._multiple_jobs_file)
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_jobs()
        assert len(jobs) == 2

        assert jobs[0].name == "BUTWHATABOUTSECONDJOB"
        assert jobs[0].gibstr == "pistaccio"
        assert jobs[0].gib_num == float("3.2")
        assert jobs[0].opt_int == 4
        assert jobs[0].opt_d == 6
        assert not jobs[0].iam_bool

        assert jobs[1].name == "THETHIRDJOB"
        assert jobs[1].gibstr == "but they were all of them deceived, for another job was made"
        assert jobs[1].gib_num == float("3.2")
        assert jobs[1].opt_int == 5
        assert jobs[1].opt_d == 16
        assert jobs[1].opt_many == [float("1"), float("4.5"), float("-3")]
        assert jobs[1].iam_bool

        # We allow setting default section name from CLI
        sys.argv = [*_sample_argv_conf(self._default_file), "--name", "funky-name"]
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "funky-name"

    @restore_argv
    def test_conf_specific_jobs(self):
        sys.argv = _sample_argv_conf(f"{self._multiple_jobs_file}:BUTWHATABOUTSECONDJOB")
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "BUTWHATABOUTSECONDJOB"

        sys.argv = _sample_argv_conf(f"{self._multiple_jobs_file}:THETHIRDJOB:BUTWHATABOUTSECONDJOB")
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_jobs()
        assert len(jobs) == 2
        assert jobs[0].name == "BUTWHATABOUTSECONDJOB"
        assert jobs[1].name == "THETHIRDJOB"

        sys.argv = _sample_argv_conf(f"{self._multiple_jobs_file}:THETHIRDJOB:FAKEJOB:BUTWHATABOUTSECONDJOB")
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        with pytest.raises(JobParserError):
            jobs = parser.parse_jobs()

    @restore_argv
    def test_missing_arg(self):
        sys.argv = _argv_template
        parser = JobParser(*_sample_arguments)
        with pytest.raises(JobParserError):
            parser.parse_job()

    @restore_argv
    def test_no_default_section(self):
        sys.argv = _sample_argv_conf(self._no_default_file)
        parser = JobParser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_job()

        assert job.name == "IAMNOTDEFAULT"
        assert job.gibstr == "not default"
        assert job.gib_num == float("3.2")
        assert job.arg_two == ["1", "2"]
        assert job.opt_default_none == [2, 3]

        sys.argv += shlex.split("--opt-default-none 1 3 5")
        parser = JobParser(*_sample_arguments, multiple_jobs=False)
        with pytest.raises(ValueError):
            parser.parse_job()

    @restore_argv
    def test_required_args(self):
        sys.argv = f"{_argv_template[0]} -c {self._multiple_jobs_file}".split()
        parser = JobParser(*_sample_arguments, multiple_jobs=True)
        with pytest.raises(JobParserError):
            parser.parse_jobs()

    @restore_argv
    def test_nargs(self):
        # Test an expected case
        sys.argv = [*_argv_template, "--bar", "1", "2"]
        parser = JobParser(
            RequiredArg("bar", nargs=2, type=int),
            OptionalArg("foo", nargs=3, default=["a", "b", "c"]),
            OptionalArg("fizz", nargs=1, default=(1,)),
        )
        assert parser._arguments["fizz"].type is int

        args = parser.parse_job()
        assert len(args.bar) == 2
        assert args.bar == [1, 2]
        assert len(args.foo) == 3
        assert args.foo == ["a", "b", "c"]

        # Test if argument not given
        sys.argv = _argv_template
        parser = JobParser(
            RequiredArg("bar", nargs=0, type=int),
        )
        with pytest.raises(JobParserError):
            parser.parse_job()

        # Test if wrong number of arguments
        sys.argv = [*_argv_template, "--bar", "1", "2"]
        parser = JobParser(RequiredArg("bar", nargs=3))
        with pytest.raises(ValueError):
            parser.parse_job()
        parser = JobParser(OptionalArg("bar", nargs=3, default=[1, 2, 3]))
        with pytest.raises(ValueError):
            parser.parse_job()

        # Make sure stuff also works if config file is wrong
        sys.argv = [*_argv_template, "-c", str(self._sample_single_nargs_file)]
        parser = JobParser(RequiredArg("foo", nargs=3))
        with pytest.raises(ValueError):
            parser.parse_job()

        # Test type parsing
        parser = JobParser(RequiredArg("foo", nargs=2, type=int))
        args = parser.parse_job()
        assert args.foo == [3, 4]

    @restore_argv
    def test_no_unknown_args(self):
        # Test with command line argument
        sys.argv = [*_argv_template, "--bar", "1", "--foo", "1"]
        parser = JobParser(RequiredArg("bar"))
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            parser.parse_job()
        assert pytest_wrapped_e.type is SystemExit
        assert pytest_wrapped_e.value.code == 2

        # Test with config argument
        sys.argv = [*_argv_template, "-c", str(self._sample_single_nargs_file)]
        parser = JobParser(OptionalArg("bar", type=int, default=[1, 2]))
        with pytest.raises(JobParserError):
            parser.parse_job()

    @restore_argv
    def test_document(self):
        output_dir = self.get_test_path(_testdir)
        docfile = output_dir / "docfile.ini"
        sys.argv = _sample_argv_conf(self._no_default_file)
        parser = JobParser(*_sample_arguments)
        job = parser.parse_job()

        job.write_documentation(docfile)
        content = docfile.read_text()
        assert _sample_no_default.replace("=", " = ").strip() in content.strip()
        assert " ".join(_sample_argv_conf(self._no_default_file)) in content

    @restore_argv
    def test_names(self):
        sys.argv = _sample_argv
        parser = JobParser(*_sample_arguments)
        job = parser.parse_job()

        # Assert that characters not friendly to filenames
        # do not appear in autogenerated names
        assert " " not in job.name
        assert ":" not in job.name
        assert "/" not in job.name
