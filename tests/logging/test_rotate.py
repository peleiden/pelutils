import os
import shutil
from datetime import datetime
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
            Rotater("1", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # Missing value
            Rotater("GB", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # Invalid value
            Rotater("1.1 GB", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # Unknown unit
            Rotater("1 gb", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # Wrong order
            Rotater("GB 1", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # Empty
            Rotater("", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # Negative
            Rotater("-1 GB", Path(self.test_dir, "log.log"))
        with pytest.raises(ValueError):
            # 0
            Rotater("0 GB", Path(self.test_dir, "log.log"))
        with pytest.raises(FileExistsError):
            # Points to a directory
            Rotater("1 GB", Path())
        with pytest.raises(FileExistsError):
            Rotater("1 GB", Path(self.test_dir))

        # Valid examples
        Rotater("1 GB", Path(self.test_dir, "log.log"))
        Rotater("1000 kB", Path(self.test_dir, "log.log"))
        Rotater("32398 MB", Path(self.test_dir, "log.log"))
        Rotater("year", Path(self.test_dir, "log.log"))
        Rotater("month", Path(self.test_dir, "log.log"))
        Rotater("day", Path(self.test_dir, "log.log"))
        Rotater("hour", Path(self.test_dir, "log.log"))
        Rotater(None, Path(self.test_dir, "log.log"))

    def test_write(self):
        self.reset()
        n = 1500
        rotater = Rotater("5 kB", Path(self.test_dir, "log.log"))
        rotater.write("0"*n)
        assert rotater.base_file.is_file()
        written = rotater.base_file.read_text()
        assert len(written) == n
        assert all(x == "0" for x in written)

    def test_size_rotate(self):
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

    def test_next_time(self):
        start_times = (
            datetime(2024, 1, 1),
            datetime(2025, 10, 2, 4),
            datetime(2026, 2, 28, 5, 30, 1, 123),
            datetime(2027, 1, 1, 23, 1, 1, 1),
            datetime(2028, 2, 29, 23, 0, 1, 59),
            datetime(2030, 10, 31, 15, 2, 3, 1231),
            datetime(2035, 12, 20, 23, 59, 59),
        )

        for unit in Rotater.supported_time_units:
            for now in start_times:
                rotater = Rotater(unit, Path(self.test_dir, "log.log"))
                rotater.current_time = rotater.get_start_time(now)
                rotater.next_time = rotater.get_next_time()

                for i in range(1000):
                    if unit == "hour":
                        assert (rotater.next_time-rotater.current_time).total_seconds() == 3600
                    if unit == "day":
                        assert rotater.current_time.hour == 0
                        assert rotater.next_time.hour == 0
                        assert (rotater.next_time-rotater.current_time).days == 1
                        assert (rotater.next_time-rotater.current_time).seconds == 0
                    if unit == "month":
                        assert rotater.current_time.hour == 0
                        assert rotater.next_time.hour == 0
                        assert rotater.current_time.day == 1
                        assert rotater.next_time.day == 1
                        if rotater.next_time.month == 1:
                            assert rotater.current_time.month == 12
                        else:
                            assert rotater.next_time.month - rotater.current_time.month == 1
                    if unit == "year":
                        assert rotater.current_time.hour == 0
                        assert rotater.next_time.hour == 0
                        assert rotater.current_time.day == 1
                        assert rotater.next_time.day == 1
                        assert rotater.current_time.month == 1
                        assert rotater.next_time.month == 1
                        assert rotater.next_time.year - rotater.current_time.year == 1

                    rotater.current_time = rotater.next_time
                    rotater.next_time = rotater.get_next_time()
