from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path


class _LogFileRotater:

    supported_time_units = ["year", "month", "day", "hour"]
    supported_size_units = ["GB", "MB", "kB"]

    def __init__(self, rotate_cmd: str | None, base_file: Path):
        self.rotate_cmd = rotate_cmd
        self.base_file = base_file
        self.value = None
        self.unit = None
        if self.rotate_cmd is not None:
            self.rotate_cmd = self.rotate_cmd.strip()
            self.value, self.unit = self.parse_rotate_cmd(self.rotate_cmd)
            if self.value is not None and self.value <= 0:
                raise ValueError(f"Rotation quantity must be positive, not {self.value}")

        self._is_time_constrained = self.unit in self.supported_time_units

        if self.is_size_constrained:
            if self.unit == "GB":
                self.max_file_size = self.value * 10 ** 9
            elif self.unit == "MB":
                self.max_file_size = self.value * 10 ** 6
            elif self.unit == "kB":
                self.max_file_size = self.value * 10 ** 3
            else:
                raise ValueError(f"Invalid size unit \"{self.unit}\", must be one of {self.supported_size_units}")

        if self.is_time_constrained:
            # Current time is the start of the current time block
            self.current_time = self.get_current_time()
            # Next time is the start of the next file block at which point the log file will change
            self.next_time = self.get_next_time()

        if self.base_file is not None and self.base_file.is_dir():
            raise FileExistsError(f"Given log file {self.base_file} already exists and is a directory")

    @property
    def is_time_constrained(self) -> bool:
        return self._is_time_constrained and self.rotate_cmd is not None

    @property
    def is_size_constrained(self) -> bool:
        return not self._is_time_constrained and self.rotate_cmd is not None

    @classmethod
    def parse_rotate_cmd(cls, rotate_cmd: str) -> tuple[int, str]:
        pattern = r"^(\d+)\s*([a-zA-Z]+)$"
        rotate_cmd = rotate_cmd.strip()
        if rotate_cmd in cls.supported_time_units:
            return 1, rotate_cmd
        match = re.search(pattern, rotate_cmd)
        if match is None:
            raise ValueError(f"Given rotate command \"{rotate_cmd}\" is invalid. It must be an integer followed by a supported unit, e.g. H (hours).")
        value = int(match.group(1))
        unit = match.group(2)
        if unit not in cls.supported_size_units:
            raise ValueError(f"Unsupported unit \"{unit}\". Must be one of {', '.join(cls.supported_size_units)}")
        return value, unit

    def write(self, text: str, mode="w", encoding="utf-8"):
        if mode not in {"w", "a"}:
            raise ValueError(f"Write mode must be either write (w) or append (a), not \"{mode}\".")
        text = text.encode(encoding)
        file = self.resolve_logfile(len(text))
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open(f"{mode}b") as f:
            f.write(text)

    def rotate_size_constrained_files(self):
        assert self.is_size_constrained
        i = 0
        current_file = str(self.base_file)
        base_file_base, base_file_ext = os.path.splitext(current_file)
        new_file = f"{base_file_base}.{i}{base_file_ext}"
        shutil.move(current_file, current_file + ".tmp")
        while os.path.isfile(new_file):
            i += 1
            shutil.move(new_file, new_file + ".tmp")
            shutil.move(current_file + ".tmp", new_file)
            current_file = new_file
            new_file = f"{base_file_base}.{i}{base_file_ext}"
        shutil.move(current_file + ".tmp", new_file)

    def get_current_time(self) -> datetime:
        now = datetime.now()
        if self.unit == "year":
            return datetime(now.year, 1, 1)
        elif self.unit == "month":
            return datetime(now.year, now.month, 1)
        elif self.unit == "day":
            return datetime(now.year, now.month, now.day)
        elif self.unit == "hour":
            return datetime(now.year, now.month, now.day, now.hour)
        raise ValueError(f"Invalid time unit \"{self.unit}\", must be one of {self.supported_time_units}")

    def get_next_time(self) -> datetime:
        next_hour = self.current_time.hour + (self.unit == "hour")
        next_day = self.current_time.day + (self.unit == "day")
        next_month = self.current_time.month + (self.unit == "month")
        next_year = self.current_time.year + (self.unit == "year")

        if next_hour == 24:
            assert self.unit == "hour"
            next_hour = 0
            next_day += 1
        if self.unit in {"hour", "day"}:
            try:
                datetime(next_year, next_month, next_day, next_hour)
            except ValueError:
                # Day is out of range
                next_day = 1
                next_month += 1
        if next_month == 13:
            next_month = 1
            next_year += 1

        return datetime(next_year, next_month, next_day, next_hour)

    def resolve_logfile(self, writesize: int) -> Path:
        """Rotates existing files if necessary and returns the file to write to."""
        if self.is_size_constrained:
            if self.base_file.is_file() and os.path.getsize(self.base_file) + writesize > self.max_file_size:
                self.rotate_size_constrained_files()
            return self.base_file

        if self.is_time_constrained:
            if datetime.now() >= self.next_time:
                # If time has passed into the next time, update the current and next time
                self.current_time = self.get_current_time()
                self.next_time = self.get_next_time()
            # Format current time
            # Format specifiers at https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
            if self.unit == "hour":
                fmt = self.current_time.strftime("%Y%m%d_%H")
            elif self.unit in {"day", "month"}:
                fmt = self.current_time.strftime("%Y%m%d")
            elif self.unit == "year":
                fmt = self.current_time.strftime("%Y")
            base_file_base, base_file_ext = os.path.splitext(self.base_file)
            return Path(f"{base_file_base}.{fmt}{base_file_ext}")

        return self.base_file
