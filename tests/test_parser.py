from __future__ import annotations
import itertools
import os
import sys

import pytest

from pelutils import except_keys
from pelutils.tests import restore_argv, MainTest
from pelutils.parser import Argument, Option, Flag, Parser, JobDescription,\
    _fixdash, ParserError, CLIError, ConfigError


_testdir = "parser_test"
_sample_argv = f"main.py {os.path.join(MainTest.test_dir, _testdir)} -g 4 --gib-num 3.2 -o 7 -i".split()
_sample_argv_conf = lambda config_path: (
    f"main.py {os.path.join(MainTest.test_dir, _testdir)} -c %s --gib-num 3.2" % config_path
).split()
_sample_arguments = [
    Argument("gibstr"),
    Argument("gib-num", type=float),
    Option("opt-int", default=4),
    Option("opt-d", abbrv="o", default=6, type=lambda x: 2 * int(x)),
    Flag("iam-bool", abbrv="i")
]

_sample_no_default = """
[IAMNOTDEFAULT]
gibstr=not default
"""
_sample_default_only = """
[DEFAULT]
gibstr=pistaccio
iam-bool
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
"""


class TestParser(MainTest):

    def setup_class(self):
        super().setup_class()
        self._no_default_file    = os.path.join(self.test_dir, "no-default.ini")
        self._default_file       = os.path.join(self.test_dir, "default-only.ini")
        self._single_job_file    = os.path.join(self.test_dir, "single-job.ini")
        self._multiple_jobs_file = os.path.join(self.test_dir, "multiple-jobs.ini")
        with open(self._no_default_file, "w") as f:
            f.write(_sample_no_default)
        with open(self._default_file, "w") as f:
            f.write(_sample_default_only)
        with open(self._single_job_file, "w") as f:
            f.write(_sample_single_section)
        with open(self._multiple_jobs_file, "w") as f:
            f.write(_sample_multiple_section)

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
        Argument("meme-folder")
        Option("memes", abbrv="m", default="doge")
        Flag("show-memes", abbrv="s")

    def test_job_description(self):
        j = JobDescription(
            name = "groot",
            location = "i_am_groot",
            explicit_args = set(),
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

    @restore_argv
    def test_name_and_abbrv_handling(self):
        """ Test that name abbreviation ordering and collisions are handled properly """
        with pytest.raises(ParserError):
            Parser(Argument("arg1", abbrv="a"), Argument("arg2", abbrv="a"))
        with pytest.raises(ParserError):
            Parser(Argument("location"))
        with pytest.raises(ParserError):
            Parser(Argument("null", abbrv="n"))

        # Test that under no permutations is the ordering changed in the argparser
        sys.argv = f"main.py {os.path.join(MainTest.test_dir, _testdir)}".split()
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

    @restore_argv
    def test_no_conf_single_job(self):
        sys.argv = _sample_argv
        parser = Parser(*_sample_arguments, multiple_jobs=False)
        job = parser.parse_args()

        assert isinstance(job, JobDescription)
        assert job.location == os.path.join(self.test_dir, _testdir)
        assert job.gibstr == "4"
        assert job.gib_num == float("3.2")
        assert job.opt_int == 4
        assert job.opt_d == 14
        assert job.iam_bool
        assert job.explicit_args == { "location", "gibstr", "gib_num", "opt_d", "iam_bool" }

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
        assert job.opt_int == 4
        assert job.opt_d == 14
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
        assert jobs[1].iam_bool

        # Make sure an error is thrown if name is set from the command line
        sys.argv = _sample_argv_conf(self._default_file) + ["--name", "forbidden-name"]
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        with pytest.raises(CLIError):
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

    @restore_argv
    def test_non_optional_args(self):
        sys.argv = f"main.py {os.path.join(MainTest.test_dir, _testdir)} -c {self._multiple_jobs_file}".split()
        parser = Parser(*_sample_arguments, multiple_jobs=True)
        with pytest.raises(ParserError):
            parser.parse_args()

    @restore_argv
    def test_clear_folders(self):
        d = os.path.join(self.test_dir, _testdir)
        os.makedirs(d)
        with open(os.path.join(d, "tmp.txt"), "w") as f:
            f.write("")
        sys.argv = f"main.py {os.path.join(MainTest.test_dir, _testdir)}".split()
        parser = Parser()
        parser.parse_args(clear_folders=True)
        assert not os.listdir(d)

