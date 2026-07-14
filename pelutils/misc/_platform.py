"""Code relating to the platform on which the code is running."""

import os
import subprocess
import sys
from functools import cached_property

import cpuinfo
import psutil
from typing_extensions import override

from pelutils.misc._conditional_import import import_torch

torch = import_torch()


class UnsupportedOS(Exception):  # noqa: N818
    """Error raised when an operation is attempted which is not supported on the current OS."""


class OS:
    """Class for checking the current OS."""

    # See https://docs.python.org/3/library/sys.html#sys.platform for all platforms
    is_windows = sys.platform == "win32"
    is_mac = sys.platform == "darwin"
    is_linux = sys.platform == "linux"


class _HardwareInfo:
    """Hardware information for the system conveniently accessible."""

    @cached_property
    def cpu(self) -> str:
        """Name of the CPU."""
        return cpuinfo.get_cpu_info()["brand_raw"]

    @cached_property
    def sockets(self) -> int | None:
        """Number of CPU sockets on the system. This currently only works for Linux."""
        if OS.is_linux:
            return int(subprocess.check_output('cat /proc/cpuinfo | grep "physical id" | sort -u | wc -l', shell=True))

    @cached_property
    def threads(self) -> int | None:
        """Total number of threads available across all CPU sockets."""
        return os.cpu_count()

    @cached_property
    def memory(self) -> int:
        """Total system memory in bytes."""
        return psutil.virtual_memory().total

    @cached_property
    def gpus(self) -> list[str] | None:
        """Attempt to get GPU names of available devices. This requires torch to be installed."""
        if torch is not None and torch.cuda.is_available():
            return [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]

    @override
    def __str__(self) -> str:
        """Pretty string-representation of hardware."""
        lines = [
            f"CPU:     {self.cpu}",
            f"Sockets: {self.sockets}" if self.sockets else None,
            f"Threads: {self.threads:,}" if self.threads else None,
            f"RAM:     {self.memory / 2**30:,.2f} GiB",
            f"GPU(s):  {self.gpus[0]}" if self.gpus else None,
            *[f"         {gpu}" for gpu in (self.gpus[1:] if self.gpus is not None and len(self.gpus) > 1 else [])],
        ]
        return "\n".join(line for line in lines if line)


hardware_info = _HardwareInfo()
