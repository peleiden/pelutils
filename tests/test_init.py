from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from shutil import move
from string import ascii_letters

import numpy as np
import pytest
import torch

import pelutils
from pelutils import (
    OS,
    UnsupportedOS,
    array_ptr,
    except_keys,
    get_repo,
    reverse_line_iterator,
)
from pelutils.tests import UnitTestCollection


class TestInit(UnitTestCollection):
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
            f.writelines(ascii_letters * 1000 + "\n" for _ in range(100))
        paths.append(os.path.join(cls.test_dir, "long_lines_with_newline_fancyness.txt"))
        with open(paths[-1], "w") as f:
            for i in range(100):
                f.write("\n")
                f.write(ascii_letters * 1000 + ("\n" if i < 99 else ""))
        return paths

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
            f.writelines(ascii_letters * n + "\n" for n in range(lines))
        assert os.path.getsize(path) == len(ascii_letters) * ((lines) ** 2 - lines) / 2 + lines

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
        d = {"a": 3, "b": 5}
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

    def test_get_repo(self):
        if ".git" in os.listdir() and pelutils.git is not None:
            a, b = get_repo()
            assert isinstance(a, str)
            assert isinstance(b, str)

        git = pelutils.git

        pelutils.git = None
        a, b = get_repo()
        assert a is None
        assert b is None

        pelutils.git = git
        if ".git" in os.listdir():
            move(".git", ".gittmp")
            a, b = get_repo()
            assert a is None
            assert b is None
            move(".gittmp", ".git")


def test_public_api():
    specialized_exports = {
        "AnyArray",
        "SimplePool",
        "UnitTestCollection",
        "dump",
        "dumps",
        "load",
        "loads",
        "restore_argv",
        "unique",
    }
    assert specialized_exports.isdisjoint(pelutils.__all__)
    assert not hasattr(pelutils, "DataStorage")
    assert not hasattr(pelutils, "raises")
    assert not hasattr(pelutils, "set_seeds")
    assert not hasattr(pelutils, "thousands_seperators")


def test_import_does_not_load_ds_or_c_extension():
    script = (
        "import sys; import pelutils; "
        "assert 'pelutils.ds' not in sys.modules; "
        "assert '_pelutils_c' not in sys.modules; "
        "assert not hasattr(pelutils, 'unique')"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
