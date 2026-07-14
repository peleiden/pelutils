import os
from string import ascii_letters

import pytest

from pelutils.misc import OS, UnsupportedOS, reverse_line_iterator
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
