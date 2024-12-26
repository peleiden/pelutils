import os
import shutil
from pathlib import Path

import pytest

from pelutils.logging.rotate import _LogFileRotater as Rotater
from pelutils.tests import UnitTestCollection

class TestRotate(UnitTestCollection):

    def reset(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

    def test_rotate_cmd(self):
        with pytest.raises(ValueError):
            # Missing unit
            Rotater("1", Path())
        with pytest.raises(ValueError):
            # Missing value
            Rotater("GB", Path())
        with pytest.raises(ValueError):
            # Invalid value
            Rotater("1.1 GB", Path())
        with pytest.raises(ValueError):
            # Unknown unit
            Rotater("1 gb", Path())
        with pytest.raises(ValueError):
            # Wrong order
            Rotater("GB 1", Path())
        with pytest.raises(ValueError):
            # Empty
            Rotater("", Path())
        with pytest.raises(ValueError):
            # Negative
            Rotater("-1 GB", Path())
        with pytest.raises(ValueError):
            # 0
            Rotater("0 GB", Path())

        # Valid examples
        Rotater("1 GB", Path())
        Rotater("1000 kB", Path())
        Rotater("32398 MB", Path())
        Rotater("23 Y", Path())
        Rotater("1 M", Path())
        Rotater("1 D", Path())
        Rotater("1 H", Path())
        Rotater(None, Path())

    def test_write(self):
        self.reset()
        n = 1500
        rotater = Rotater("5 kB", Path(self.test_dir, "log.log"))
        rotater.write("0"*n)
        assert rotater.base_file.is_file()
        written = rotater.base_file.read_text()
        assert len(written) == n
        assert all(x == "0" for x in written)

    def test_rotate(self):
        self.reset()
        n = 1500
        rotater = Rotater("5 kB", Path(self.test_dir, "log.log"))
        for i in range(10):
            s = n * f"{i}"
            rotater.write(s, "a")
            written = rotater.base_file.read_text()
            assert s in written
            assert os.path.getsize(rotater.base_file) <= 5 * 10 ** 3
        for file in sorted(rotater.base_file.parent.glob("log.*.log")):
            assert os.path.getsize(file) == n * ((5 * 10 ** 3) // n)
        assert os.path.getsize(rotater.base_file) == 1500
