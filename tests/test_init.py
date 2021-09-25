from __future__ import annotations
from string import ascii_letters
import io
import os

import numpy as np

from pelutils import EnvVars, reverse_line_iterator, except_keys,\
    split_path, binary_search, raises, thousands_seperators
from pelutils.tests import MainTest


class TestInit(MainTest):

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
        )
        for num, with_dot, with_comma in cases:
            for neg in False, True:
                if neg == -1:
                    num = -num
                    with_dot = "-" + with_dot
                    with_comma = "-" + with_comma
                assert with_dot == thousands_seperators(num, ".")
                assert with_comma == thousands_seperators(num, ",")

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
            f.write("abc\nbbc\n")
        paths.append(os.path.join(cls.test_dir, "no_end_newline.txt"))
        with open(paths[-1], "w") as f:
            f.write("abc\nbbc")
        paths.append(os.path.join(cls.test_dir, "start_newline.txt"))
        with open(paths[-1], "w") as f:
            f.write("\na\nb\n")
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

    def test_reverse_line_iterator(self):
        # Test reverse iteration
        for file in self._setup_lineiter_files():
            with open(file) as f:
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
