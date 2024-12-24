from __future__ import annotations

import ctypes
import os
import platform
from string import ascii_letters
from shutil import move

import numpy as np
import pytest
import torch

import pelutils
from pelutils import EnvVars, UnsupportedOS, reverse_line_iterator, except_keys,\
    split_path, binary_search, raises, thousands_seperators, OS, array_ptr,\
    get_timestamp, get_timestamp_for_files, HardwareInfo, get_repo
from pelutils.tests import UnitTestCollection

class TestInit(UnitTestCollection):

    def test_envvars(self):
        os.environ["var1"] = "v1"
        assert os.environ["var1"] == "v1"
        assert "var2" not in os.environ
        with EnvVars(var1="v2", var2=2):
            assert os.environ["var1"] == "v2"
            assert os.environ["var2"] == "2"
        assert os.environ["var1"] == "v1"
        assert "var2" not in os.environ

    def test_split_path(self):
        empty = ""
        assert split_path(empty) == ["."]
        root = "/"
        assert split_path(root) == ["", ""]
        absolute = "/home/senate"
        assert split_path(absolute) == ["", "home", "senate"]
        assert split_path(absolute + "/") == ["", "home", "senate"]
        relative = "use/pelutils/pls.py"
        assert split_path(relative) == ["use", "pelutils", "pls.py"]

    def test_thousands_seperator(self):
        cases = (
            (1, "1", "1"),
            (1.1, "1.1", "1,1"),
            (1e3, "1,000.0", "1.000,0"),
            (1.234567e4, "12,345.67", "12.345,67"),
            (1234567890, "1,234,567,890", "1.234.567.890"),
            (0.03413, "0.03413", "0,03413"),
            (-0.03413, "-0.03413", "-0,03413"),
        )
        for num, with_dot, with_comma in cases:
            for neg in False, True:
                if neg == -1:
                    num = -num
                    with_dot = "-" + with_dot
                    with_comma = "-" + with_comma
                with pytest.warns(DeprecationWarning):
                    assert with_dot == thousands_seperators(num, ".")
                with pytest.warns(DeprecationWarning):
                    assert with_comma == thousands_seperators(num, ",")

        with pytest.raises(ValueError), pytest.warns(DeprecationWarning):
            thousands_seperators(1, "a")

    def test_raises(self):
        assert raises(IndexError, lambda x: x[0], [])
        assert not raises(IndexError, lambda x: x[0], [1])
        assert not raises(TypeError, lambda x: x[0], [])

    def test_binary_search(self):
        data = np.random.randint(0, 100, 100)
        data = np.sort(data)
        for elem in data:
            assert binary_search(elem, data) is not None
            assert data[binary_search(elem, data)] == elem
        assert binary_search(-1, data) is None
        assert binary_search(100, data) is None

    @classmethod
    def _setup_lineiter_files(cls) -> list[str]:
        paths = list()
        paths.append(os.path.join(cls.test_dir, "simple.txt"))
        with open(paths[-1], "w") as f:
            f.write(f"abc\nbbc\n")
        paths.append(os.path.join(cls.test_dir, "no_end_newline.txt"))
        with open(paths[-1], "w") as f:
            f.write(f"abc\nbbc")
        paths.append(os.path.join(cls.test_dir, "start_newline.txt"))
        with open(paths[-1], "w") as f:
            f.write(f"\na\nb\n")
        paths.append(os.path.join(cls.test_dir, "long_lines.txt"))
        with open(paths[-1], "w") as f:
            for _ in range(100):
                f.write(ascii_letters*1000 + "\n")
        paths.append(os.path.join(cls.test_dir, "long_lines_with_newline_fancyness.txt"))
        with open(paths[-1], "w") as f:
            for i in range(100):
                f.write("\n")
                f.write(ascii_letters*1000 + ("\n" if i < 99 else ""))
        return paths

    def test_is_windows(self):
        # What a dumb test
        assert OS.is_windows == platform.platform().startswith("Windows")

    def test_is_mac(self):
        # What a dumb test
        assert OS.is_mac == (platform.platform().startswith("Darwin") or platform.platform().startswith("macOS"))

    def test_is_linux(self):
        # What a dumb test
        assert OS.is_linux == platform.platform().startswith("Linux")

    def test_reverse_line_iterator(self):
        if OS.is_windows:
            open("test.txt", "w").close()
            with pytest.raises(UnsupportedOS), open("test.txt") as f:
                next(reverse_line_iterator(f))
            return

        # Test reverse iteration
        for file in self._setup_lineiter_files():
            with open(file) as f:
                with pytest.raises(ValueError):
                    next(reverse_line_iterator(f, linesep="\r\n"))
                c = f.readlines()
                f.seek(0)
                assert c[::-1] == list(reverse_line_iterator(f))
                assert f.tell() == 0

        # Truncation test
        # This tests that it is safe to truncate the file while doing reverse iteration
        path = os.path.join(self.test_dir, "truncate.txt")
        lines = 1000
        with open(path, "w") as f:
            for n in range(lines):
                f.write(ascii_letters*n + "\n")
        assert os.path.getsize(path) == len(ascii_letters) * ((lines)**2 - lines) / 2 + lines

        prev_size = os.path.getsize(path)
        with open(path, "r+") as f:
            for content in reverse_line_iterator(f):
                lines -= 1
                assert content == ascii_letters * lines + "\n"
                f.truncate()
                size = os.path.getsize(path)
                assert size <= prev_size
                prev_size = size

    def test_except_keys(self):
        d = { "a": 3, "b": 5 }
        d2 = except_keys(d, ["b", "c"])
        assert "a" in d and "b" in d
        assert "a" in d2 and "b" not in d2

    def test_array_ptr(self):
        with pytest.raises(TypeError):
            array_ptr(None)
        with pytest.raises(ValueError):
            array_ptr(np.arange(5)[::2])
        assert isinstance(array_ptr(torch.arange(5)), ctypes.c_void_p)
        a = torch.arange(5)
        assert array_ptr(a).value == array_ptr(a.numpy()).value

    def test_get_timestamp(self):
        for date in False, True:
            ts0 = get_timestamp(with_date=date)
            ts1 = get_timestamp_for_files(with_date=date)
            assert len(ts0[:-4]) == len(ts1)
            assert ts1 == ts0[:-4].replace(" ", "_").replace(":", "-")

    def test_hardware_info(self):
        assert isinstance(HardwareInfo.cpu, str) and len(HardwareInfo.cpu) > 0
        if OS.is_linux:
            assert isinstance(HardwareInfo.sockets, int) and HardwareInfo.sockets >= 1
        else:
            assert HardwareInfo.sockets is None
        assert isinstance(HardwareInfo.threads, int) and HardwareInfo.threads > 0
        assert isinstance(HardwareInfo.memory, int) and HardwareInfo.memory > 0
        if torch.cuda.is_available():
            assert isinstance(HardwareInfo.gpus, list)
            assert len(HardwareInfo.gpus) > 0
            for gpu in HardwareInfo.gpus:
                assert isinstance(gpu, str)
        else:
            assert HardwareInfo.gpus is None

        string = HardwareInfo.string()
        assert HardwareInfo.cpu in string
        if HardwareInfo.sockets:
            # This is a very shitty test
            assert str(HardwareInfo.sockets) in string
        if HardwareInfo.threads:
            # This is also a very shitty test
            with pytest.warns(DeprecationWarning):
                assert thousands_seperators(HardwareInfo.threads) in string
        assert str(round(HardwareInfo.memory / 2 ** 30, 2)) in string
        if HardwareInfo.gpus:
            for gpu in HardwareInfo.gpus:
                assert gpu in string

    def test_get_repo(self):
        if ".git" in os.listdir() and pelutils._has_git:
            a, b = get_repo()
            assert isinstance(a, str)
            assert isinstance(b, str)

        pelutils._has_git = False
        a, b = get_repo()
        assert a is None
        assert b is None

        pelutils._has_git = True
        if ".git" in os.listdir():
            move(".git", ".gittmp")
            a, b = get_repo()
            assert a is None
            assert b is None
            move(".gittmp", ".git")
