from __future__ import annotations
import itertools
import os
import shutil
import sys

import pytest

from pelutils import except_keys
from pelutils.tests import restore_argv, UnitTestCollection
from pelutils.parser import Argument, Option, Flag, Parser, JobDescription, \
    _fixdash, ParserError, ConfigError


_testdir = "parser_test"
_argv_template = ["main.py", os.path.join(UnitTestCollection.test_dir, _testdir)]
_sample_argv = f"{_argv_template[0]} {_argv_template[1]} -g 4 --gib-num 3.2 -o 7 -i -a b c".split()
_sample_argv_conf = lambda config_path: (
    f"{_argv_template[0]} {_argv_template[1]} -c %s --gib-num 3.2" % config_path
).split()
_sample_arguments = [
    Argument("gibstr"),
    Argument("gib-num", type=float),
    Argument("arg-two", nargs=2),
    Option("opt-int", default=4),
    Option("opt-d", abbrv="o", default=6, type=lambda x: 2 * int(x)),
    Option("opt-many", nargs=0, default=list(), type=float),
    Option("hello", default="there"),
    Option("Cased-Option", default="Kebab-Pascal"),
    Flag("iam-bool", abbrv="i"),
    Flag("Cased-Flag"),
]

_sample_no_default = """
[IAMNOTDEFAULT]
gibstr=not default
arg-two=1 2
"""
_sample_default_only = """
[DEFAULT]
gibstr=pistaccio
arg-two=1 2
Cased-Option=Pascal-Kebab
iam-bool
Cased-Flag
"""
_sample_single_section = _sample_default_only + """
[BUTWHATABOUTSECONDJOB]
iam-bool=False
gib-num=5
"""
_sample_multiple_section = _sample_single_section + """
[THETHIRDJOB]
gibstr=but they were all of them deceived, for another job was made
opt-d=8
opt-int=5
iam-bool=True
arg-two=1 3
opt-many=1 4.5 -3
"""
_sample_single_nargs = """
[DEFAULT]
foo=3 4
"""


class TestParser(UnitTestCollection):

    def setup_class(self):
        super().setup_class()
        self._no_default_file          = os.path.join(self.test_dir, "no-default.ini")
        self._default_file             = os.path.join(self.test_dir, "default-only.ini")
        self._single_job_file          = os.path.join(self.test_dir, "single-job.ini")
        self._multiple_jobs_file       = os.path.join(self.test_dir, "multiple-jobs.ini")
        self._sample_single_nargs_file = os.path.join(self.test_dir, "single-nargs.ini")
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
            Argument("")
        with pytest.raises(ValueError):
            Option("--Hello there", default="General Kenobi")
        with pytest.raises(ValueError):
            Flag("show-memes", abbrv="sm")
        with pytest.raises(ValueError):
            Option("memes", abbrv="-s", default="doge")
        with pytest.raises(ValueError):
            Flag("-show-memes")
        for char in (" ", "\t", "\n"):
            with pytest.raises(ValueError):
                Argument("hello%sthere" % char)
        with pytest.raises(TypeError):
            Argument("default", default=4)
        with pytest.raises(TypeError):
            Argument("multiple-args", nargs="?")
        with pytest.raises(ValueError):
            Option("no-args", nargs=-1, default=[])
        Argument("meme-folder")
        Option("memes", abbrv="m", default="doge")
        Flag("show-memes", abbrv="s")

    def test_job_description(self):
        j = JobDescription(
            name = "groot",
            location = "i_am_groot",
            explicit_args = set(),
            docfile_content = "",
            a = 2,
            a_b = 4,
        )
        assert j.name == j["name"]
        assert j.a == j["a"]
        assert j.a_b == j["a_b"]
        assert j.a_b == j["a-b"]
        with pytest.raises(KeyError):
            j["ab"]
        with pytest.raises(AttributeError):
            j.ab

        job_dict = j.todict()
        for kw, v in job_dict.items():
            assert getattr(j, kw) == v
            assert not kw.startswith("_")
            assert kw != "explicit_args"

    @restore_argv
    def test_job_description_format(self):
        sys.argv = _sample_argv
        parser = Parser(*_sample_arguments)

        job = parser.parse_args()
        for arg in _sample_arguments:
            assert _fixdash(arg.name) in str(job)

    def test_argument_format(self):
        for arg in _sample_arguments:
            assert arg.name in str(arg)
            assert arg.__class__.__name__ in str(arg)

    def test_argument_hash(self):
        assert hash(Argument("name")) == hash(Option("name")) == hash(Flag("name"))
        assert hash(Argument("name")) != hash(Option("namer")) != hash(Flag("namerr"))

    @restore_argv
    def test_name_and_abbrv_handling(self):
        """ Test that name abbreviation ordering and collisions are handled properly """
        with pytest.raises(ParserError):
            Parser(Argument("arg1", abbrv="a"), Argument("arg2", abbrv="a"))
        with pytest.raises(ParserError):
            Parser(Argument("location"))
        with pytest.raises(ParserError):
            Parser(Argument("help"))

        # Test that under no permutations is the ordering changed in the argparser
        sys.argv = f"main.py {os.path.join(UnitTestCollection.test_dir, _testdir)}".split()
        sample_args = [
            Option("quick-mafs", default=0),
            Flag("Quick-flag", abbrv="Q"),
            Option("quick-boi", abbrv="q", default=1),
        ]
        for ordering in itertools.permutations(range(len(sample_args))):
            p = Parser(*(sample_args[i] for i in ordering))
            args = p._argparser.parse_args()
            for i, (argname, value) in enumerate(
                except_keys(vars(args), [_fixdash(x) for x in Parser._reserved_names])
                    .items()
            ):
                arg = sample_args[ordering[i]]
                assert _fixdash(arg.name) == argname
                assert arg.default == value

        # Test naming conflicts
        with pytest.raises(ParserError):
            Parser(Argument("a-b"), Flag("a_b"))

    def test_parser_properties(self):
        assert Parser().reserved_names == { "location", "config", "name", "help" }
        assert Parser().reserved_abbrvs == { "c" }
        assert Parser().encoding_seperator == Parser._encoding_separator

    @restore_argv
    def test_no_conf_single_job(self):
        sys.argv = _sample_argv
        parser = Parser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_args()

        assert isinstance(job, JobDescription)
        assert job.location == os.path.join(self.test_dir, _testdir)
        assert job.gibstr == "4"
        assert job.gib_num == float("3.2")
        assert job.arg_two == ["b", "c"]
        assert job.opt_int == 4
        assert job.opt_d == 14
        assert job.opt_many == list()
        assert job.iam_bool
        assert job.explicit_args == { "location", "gibstr", "gib_num", "arg_two", "opt_d", "iam_bool" }

    @restore_argv
    def test_conf_single_job(self):
        # Test with only default section
        sys.argv = _sample_argv_conf(self._single_job_file)
        parser = Parser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_args()

        assert job.name == "BUTWHATABOUTSECONDJOB"
        assert job.location == os.path.join(self.test_dir, _testdir)
        assert job.gibstr == "pistaccio"
        assert job.gib_num == float("3.2")
        assert job.opt_int == 4
        assert job.opt_d == 6
        assert not job.iam_bool

        # Test that multiple sections throws an error, unless DEFAULT is one of only two sections
        sys.argv = _sample_argv_conf(self._single_job_file)
        parser = Parser(*_sample_arguments, multiple_jobs=False)
        parser.parse_args()

        sys.argv = _sample_argv_conf(self._multiple_jobs_file)
        parser = Parser(*_sample_arguments, multiple_jobs=False)
        with pytest.raises(ConfigError):
            parser.parse_args()

    @restore_argv
    def test_no_conf_multiple_jobs(self):
        sys.argv = _sample_argv + ["--name", "good-name"]
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_args()
        assert len(jobs) == 1
        job = jobs[0]

        assert job.name == "good-name"
        assert job.location == os.path.join(self.test_dir, _testdir, job.name)
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
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_args()
        assert len(jobs) == 2

        assert jobs[0].name == "BUTWHATABOUTSECONDJOB"
        assert jobs[0].location == os.path.join(self.test_dir, _testdir, jobs[0].name)
        assert jobs[0].gibstr == "pistaccio"
        assert jobs[0].gib_num == float("3.2")
        assert jobs[0].opt_int == 4
        assert jobs[0].opt_d == 6
        assert not jobs[0].iam_bool

        assert jobs[1].name == "THETHIRDJOB"
        assert jobs[1].location == os.path.join(self.test_dir, _testdir, jobs[1].name)
        assert jobs[1].gibstr == "but they were all of them deceived, for another job was made"
        assert jobs[1].gib_num == float("3.2")
        assert jobs[1].opt_int == 5
        assert jobs[1].opt_d == 16
        assert jobs[1].opt_many == [float("1"), float("4.5"), float("-3")]
        assert jobs[1].iam_bool

        # We allow setting default section name from CLI
        sys.argv = _sample_argv_conf(self._default_file) + ["--name", "funky-name"]
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_args()
        assert len(jobs) == 1
        assert jobs[0].name == "funky-name"
        assert jobs[0].location == os.path.join(self.test_dir, _testdir, "funky-name")

    @restore_argv
    def test_conf_specific_jobs(self):
        sys.argv = _sample_argv_conf(f"{self._multiple_jobs_file}:BUTWHATABOUTSECONDJOB")
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_args()
        assert len(jobs) == 1
        assert jobs[0].name == "BUTWHATABOUTSECONDJOB"

        sys.argv = _sample_argv_conf(f"{self._multiple_jobs_file}:THETHIRDJOB:BUTWHATABOUTSECONDJOB")
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        jobs = parser.parse_args()
        assert len(jobs) == 2
        assert jobs[0].name == "BUTWHATABOUTSECONDJOB"
        assert jobs[1].name == "THETHIRDJOB"

        sys.argv = _sample_argv_conf(f"{self._multiple_jobs_file}:THETHIRDJOB:FAKEJOB:BUTWHATABOUTSECONDJOB")
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        with pytest.raises(ParserError):
            jobs = parser.parse_args()

    @restore_argv
    def test_missing_arg(self):
        sys.argv = _argv_template
        parser = Parser(*_sample_arguments)
        with pytest.raises(ParserError):
            parser.parse_args()

    @restore_argv
    def test_no_default_section(self):
        sys.argv = _sample_argv_conf(self._no_default_file)
        parser = Parser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_args()

        assert job.name == "IAMNOTDEFAULT"
        assert job.location == os.path.join(self.test_dir, _testdir)
        assert job.gibstr == "not default"
        assert job.gib_num == float("3.2")
        assert job.arg_two == ["1", "2"]

    @restore_argv
    def test_non_optional_args(self):
        sys.argv = f"main.py {os.path.join(UnitTestCollection.test_dir, _testdir)} -c {self._multiple_jobs_file}".split()
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        with pytest.raises(ParserError):
            parser.parse_args()

    @restore_argv
    def test_clear_folders(self):
        d = os.path.join(self.test_dir, _testdir)
        os.makedirs(d)
        with open(os.path.join(d, "tmp.txt"), "w") as f:
            f.write("")
        sys.argv = f"main.py {os.path.join(UnitTestCollection.test_dir, _testdir)}".split()
        parser = Parser()
        parser.parse_args()
        assert os.listdir(d)
        job = parser.parse_args()
        job.prepare_directory()
        assert len(os.listdir(d)) == 1 and os.listdir(d)[0] == JobDescription.document_filename

    @restore_argv
    def test_nargs(self):
        # Test an expected case
        sys.argv = _argv_template + ["--bar", "1", "2"]
        parser = Parser(
            Argument("bar", nargs=2, type=int),
            Option("foo", nargs=3, default=["a", "b", "c"]),
            Option("fizz", nargs=1, default=(1,))
        )
        assert parser._arguments["fizz"].type is int

        args = parser.parse_args()
        assert len(args.bar) == 2
        assert args.bar == [1, 2]
        assert len(args.foo) == 3
        assert args.foo == ["a", "b", "c"]

        # Test if argument not given
        sys.argv = _argv_template
        parser = Parser(
            Argument("bar", nargs=0, type=int),
        )
        with pytest.raises(ParserError):
            parser.parse_args()

        # Test if wrong number of arguments
        sys.argv = _argv_template + ["--bar", "1", "2"]
        parser = Parser(
            Argument("bar", nargs=3)
        )
        with pytest.raises(ValueError):
            parser.parse_args()
        parser = Parser(
            Option("bar", nargs=3, default=[1, 2, 3])
        )
        with pytest.raises(ValueError):
            parser.parse_args()

        # Make sure stuff also works if config file is wrong
        sys.argv = _argv_template + ["-c", self._sample_single_nargs_file]
        parser = Parser(
            Argument("foo", nargs=3)
        )
        with pytest.raises(ValueError):
            parser.parse_args()

        # Test type parsing
        parser = Parser(Argument("foo", nargs=2, type=int))
        args = parser.parse_args()
        assert args.foo == [3, 4]

    @restore_argv
    def test_no_unknown_args(self):
        # Test with command line argument
        sys.argv = _argv_template + ["--bar", "1", "--foo", "1"]
        parser = Parser(Argument("bar"))
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            parser.parse_args()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 2

        # Test with config argument
        sys.argv = _argv_template + ["-c", self._sample_single_nargs_file]
        parser = Parser(Option("bar", type=int, default=[1, 2]))
        with pytest.raises(ParserError):
            parser.parse_args()

    @restore_argv
    def test_document(self):
        shutil.rmtree(os.path.join(UnitTestCollection.test_dir, _testdir))
        sys.argv = _sample_argv_conf(self._no_default_file)
        parser = Parser(*_sample_arguments)
        job = parser.parse_args()
        job.prepare_directory()

        with open(os.path.join(job.location, job.document_filename)) as fh:
            content = fh.read()
        assert _sample_no_default.replace("=", " = ").strip() in content.strip()
        assert " ".join(_sample_argv_conf(self._no_default_file)) in content

        # Write documentation manually again
        job.write_documentation()
        with open(os.path.join(job.location, job.document_filename)) as fh:
            content2 = fh.read()
        assert content2 == 2 * content

    @restore_argv
    def test_names(self):
        sys.argv = _sample_argv
        parser = Parser(*_sample_arguments)
        job = parser.parse_args()

        # Assert that characters not friendly to filenames
        # do not appear in autogenerated names
        assert " " not in job.name
        assert ":" not in job.name
        assert "/" not in job.name
