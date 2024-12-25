from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


class _LogFileRotater:

    supported_time_units = ["Y", "M", "D", "H"]
    supported_size_units = ["GB", "MB", "kB"]
    supported_units = supported_time_units + supported_size_units

    def __init__(self, rotate_cmd: str | None, base_file: Path):
        self.rotate_cmd = rotate_cmd
        self.base_file = base_file
        self.value = None
        self.unit = None
        if self.rotate_cmd is not None:
            self.value, self.unit = self.parse_rotate_cmd(self.rotate_cmd)

        self._is_time_constrained = self.unit in self.supported_time_units
        if self.is_size_constrained:
            if self.unit == "GB":
                self.max_file_size = self.value * 10 ** 9
            elif self.unit == "MB":
                self.max_file_size = self.value * 10 ** 6
            elif self.unit == "kB":
                self.max_file_size = self.value * 10 ** 3
            else:
                raise ValueError(f"Invalid size unit \"{self.unit}\"")

    @property
    def is_time_constrained(self) -> bool:
        return self._is_time_constrained

    @property
    def is_size_constrained(self) -> bool:
        return not self._is_time_constrained

    @classmethod
    def parse_rotate_cmd(cls, rotate_cmd: str) -> tuple[int, str]:
        pattern = r"^(\d+)\s*([a-zA-Z]+)$"
        match = re.search(pattern, rotate_cmd)
        if match is None:
            raise ValueError(f"Given rotate command \"{rotate_cmd}\" is invalid. It must be an integer followed by a supported unit, e.g. H (for hours).")
        value = int(match.group(1))
        unit = match.group(2)
        if unit not in cls.supported_units:
            raise ValueError(f"Unsupported unit \"{unit}\". Must be one of {', '.join(cls.supported_units)}")
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
        print("Rotating")
        i = 0
        current_file = str(self.base_file)
        base_file_base, base_file_ext = os.path.splitext(current_file)
        new_file = f"{base_file_base}.{i}{base_file_ext}"
        shutil.move(current_file, current_file + ".tmp")
        print(current_file, new_file)
        while os.path.isfile(new_file):
            i += 1
            shutil.move(new_file, new_file + ".tmp")
            shutil.move(current_file + ".tmp", new_file)
            current_file = new_file
            new_file = f"{base_file_base}.{i}{base_file_ext}"
        shutil.move(current_file + ".tmp", new_file)

    def resolve_logfile(self, writesize: int) -> Path:
        """Rotates existing files if necessary and returns the file to write to."""
        if self.rotate_cmd is None:
            return self.base_file

        if self.is_size_constrained:
            print(f"{os.path.getsize(self.base_file) if self.base_file.is_file() else 0:,} {writesize:,} {self.max_file_size:,}")
            if self.base_file.is_file() and os.path.getsize(self.base_file) + writesize > self.max_file_size:
                self.rotate_size_constrained_files()
            return self.base_file


if __name__ == "__main__":
    # Temporary, for testing
    shutil.rmtree("logs", ignore_errors=True)
    rotater = _LogFileRotater("5 kB", Path("logs/log.txt"))
    for i in range(10):
        rotater.write(f"{i}"*1500 + "\n", "a")
