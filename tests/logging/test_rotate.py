import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from freezegun import freeze_time

from pelutils.logging._rotate import _LogFileRotater as Rotater
from pelutils.tests import UnitTestCollection

start_times = (
    datetime(2024, 1, 1),
    datetime(2025, 10, 2, 4),
    datetime(2026, 2, 28, 5, 30, 1, 123),
    datetime(2027, 1, 1, 23, 1, 1, 1),
    datetime(2028, 2, 29, 23, 0, 1, 59),
    datetime(2030, 10, 31, 15, 2, 3, 1231),
    datetime(2035, 12, 20, 23, 59, 59),
)

class TestRotate(UnitTestCollection):

    def reset(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

    @property
    def logfile(self) -> Path:
        return Path(self.test_dir, "log.log")

    def test_rotate_cmd(self):
        with pytest.raises(ValueError):
            # Missing unit
            Rotater("1", self.logfile)
        with pytest.raises(ValueError):
            # Missing value
            Rotater("GB", self.logfile)
        with pytest.raises(ValueError):
            # Invalid value
            Rotater("1.1 GB", self.logfile)
        with pytest.raises(ValueError):
            # Unknown unit
            Rotater("1 gb", self.logfile)
        with pytest.raises(ValueError):
            # Wrong order
            Rotater("GB 1", self.logfile)
        with pytest.raises(ValueError):
            # Empty
            Rotater("", self.logfile)
        with pytest.raises(ValueError):
            # Negative
            Rotater("-1 GB", self.logfile)
        with pytest.raises(ValueError):
            # 0
            Rotater("0 GB", self.logfile)
        with pytest.raises(FileExistsError):
            # Points to a directory
            Rotater("1 GB", Path())
        with pytest.raises(FileExistsError):
            Rotater("1 GB", Path(self.test_dir))

        # Valid examples
        Rotater("1 GB", self.logfile)
        Rotater("1000 kB", self.logfile)
        Rotater("32398 MB", self.logfile)
        Rotater("year", self.logfile)
        Rotater("month", self.logfile)
        Rotater("day", self.logfile)
        Rotater("hour", self.logfile)
        Rotater(None, self.logfile)

    def test_write(self):
        self.reset()
        n = 1500
        rotater = Rotater("5 kB", self.logfile)
        rotater.write("0"*n)
        assert rotater.base_file.is_file()
        written = rotater.base_file.read_text()
        assert len(written) == n
        assert all(x == "0" for x in written)

    def test_size_rotate(self):
        self.reset()
        n = 1500
        rotater = Rotater("5 kB", self.logfile)
        for i in range(10):
            s = n * f"{i}"
            rotater.write(s, "a")
            written = rotater.base_file.read_text()
            assert s in written
            assert os.path.getsize(rotater.base_file) <= 5 * 10 ** 3
        for file in sorted(rotater.base_file.parent.glob("log.*.log")):
            assert os.path.getsize(file) == n * ((5 * 10 ** 3) // n)
        assert os.path.getsize(rotater.base_file) == 1500

    def test_time_rotate(self):
        for unit in Rotater.supported_time_units:
            for now in start_times:
                self.reset()
                freezer = freeze_time(now)
                freezer.start()
                rotater = Rotater(unit, self.logfile)
                rotater.write("")
                files = sorted(self.logfile.parent.glob("*.log"))
                assert not self.logfile.is_file()
                assert len(files) == 1
                fname = files[0].name
                assert f".{now.year:04}" in fname
                if unit == "hour":
                    assert f"_{now.hour:02}." in fname
                freezer.stop()

                now += timedelta(3213, 28137)
                freezer = freeze_time(now)
                freezer.start()
                rotater.write("")
                files = sorted(self.logfile.parent.glob("*.log"))
                assert not self.logfile.is_file()
                assert len(files) == 2
                fname = files[1].name
                assert f".{now.year:04}" in fname
                if unit == "hour":
                    assert f"_{now.hour:02}." in fname
                freezer.stop()

    def test_next_time(self):

        for unit in Rotater.supported_time_units:
            for now in start_times:
                freezer = freeze_time(now)
                freezer.start()
                rotater = Rotater(unit, self.logfile)

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
                freezer.stop()

    def test_resolve(self):
        """Test resolution with no constraints: Should always return the base file."""
        self.reset()
        rotater = Rotater(None, self.logfile)
        for write_size in np.geomspace(1, 5e9, 10, dtype=np.uint64):
            assert rotater.resolve_logfile(write_size) == rotater.base_file

    def test_size_resolve(self):
        for size in ("1 kB", "10 kB", "1 MB", "10 MB", "1 GB", "10 GB"):
            for write_size in np.geomspace(1, 5e9, 10, dtype=np.uint64):
                self.reset()
                rotater = Rotater(size, self.logfile)
                rotater.write("")
                assert len(list(rotater.base_file.parent.glob("*.log"))) == 1
                rotater.resolve_logfile(write_size)
                rotater.write("")
                if write_size > rotater.max_file_size:
                    assert len(list(rotater.base_file.parent.glob("*.log"))) == 2
                else:
                    assert len(list(rotater.base_file.parent.glob("*.log"))) == 1
