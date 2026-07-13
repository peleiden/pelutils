from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from collections.abc import Generator, Iterable, Sequence
from datetime import datetime
from io import DEFAULT_BUFFER_SIZE
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, TypeVar

import cpuinfo

try:
    # If git is not installed, this import fails
    import git

    _has_git = True
except ImportError:
    _has_git = False
import numpy as np
import psutil

try:
    import torch

    _has_torch = True
except ModuleNotFoundError:
    _has_torch = False

if TYPE_CHECKING:
    from .types import AnyArray


_T = TypeVar("_T")


class UnsupportedOS(Exception):  # noqa: N818
    """Error raised when an operation is attempted which is not supported on the current OS."""


class OS:
    """Class for checking the current OS."""

    # See https://docs.python.org/3/library/sys.html#sys.platform for all platforms
    is_windows = sys.platform == "win32"
    is_mac = sys.platform == "darwin"
    is_linux = sys.platform == "linux"


def get_repo(path: str | Path | None = None) -> tuple[str | None, str | None]:
    """Return absolute path of git repository and commit SHA.

    Searches for repo by searching upwards from given directory (if None: uses working dir).
    If it cannot find a repository, returns (None, None).
    """
    if not _has_git:
        return None, None
    if path is None:
        path = os.getcwd()
    path = str(path)
    cdir = os.path.join(path, ".")
    pdir = os.path.dirname(cdir)
    while cdir != pdir:
        cdir = pdir
        try:  # Check if repository
            repo = git.Repo(cdir)  # pyright: ignore[reportPossiblyUnboundVariable]
            return os.path.realpath(cdir), str(repo.head.commit)
        except git.InvalidGitRepositoryError:  # pyright: ignore[reportPossiblyUnboundVariable]
            pass
        pdir = os.path.dirname(cdir)

    return None, None


def get_timestamp(*, with_date: bool = True) -> str:
    """Return a timestamp formatted as YYYY-MM-DD HH:mm:SS.ms."""
    tstr = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    if not with_date:
        tstr = tstr[11:]
    return tstr


def get_timestamp_for_files(*, with_date: bool = True) -> str:
    """Return a timestamp formatted as YYYY-MM-DD_HH-mm-SS."""
    tstr = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not with_date:
        tstr = tstr[11:]
    return tstr


class EnvVars:
    """Execute a piece of code with certain environment variables.

    ALl environment variables are restored after with block.
    Example: Disabling multithreading in tesseract:
    ```
    with EnvVars(OMP_THREAD_LIMIT=1):
        # Tesseract code here
    ```
    Any existing environment variables are restored, and newly added are removed after exiting with block.
    """

    def __init__(self, **env_vars: Any):  # pyright: ignore[reportExplicitAny]
        self._vars = env_vars
        self._original_env_vars: dict[str, str | None] = dict()

    def __enter__(self):
        """Store a copy of the currently active environment variables and set the new."""
        self._original_env_vars = dict()
        for var, value in self._vars.items():
            self._original_env_vars[var] = os.environ.get(var)
            os.environ[var] = str(value)

    def __exit__(self, *_):
        """Reset environment variables to their original values."""
        for var, value in self._original_env_vars.items():
            if value is None:
                del os.environ[var]
            else:
                os.environ[var] = value


def array_ptr(arr: "AnyArray | torch.Tensor") -> ctypes.c_void_p:
    """Return a pointer to a numpy array or torch tensor which can be used to interact with it in low-level languages like C/C++/Rust.

    This function is mostly useful when not using Python's C api and instead interfacing with .so files directly with ctypes.
    """
    if _has_torch and isinstance(arr, torch.Tensor):  # pyright: ignore[reportPossiblyUnboundVariable]
        return ctypes.c_void_p(arr.data_ptr())
    if not isinstance(arr, np.ndarray):
        raise TypeError(f"Array should be of type np.ndarray or torch.Tensor, not {type(arr)}")
    if not arr.flags.c_contiguous:
        raise ValueError("Array must be C-contiguous")
    return ctypes.c_void_p(arr.ctypes.data)


def split_path(path: str) -> list[str]:
    """Split a path into components."""
    return os.path.normpath(path).split(os.sep)


def binary_search(element: _T, iterable: Sequence[_T], *, _start: int = 0, _end: int = -1) -> int | None:
    """Get the index of element in sequence using binary search.

    The iterable is assumed to be sorted in ascending order.
    None is returned if the element is not found.
    """
    if _end == -1:  # Entered on first call
        _end = len(iterable)
        # Make sure element actually exists in array
        if not iterable[0] <= element <= iterable[-1]:  # pyright: ignore[reportOperatorIssue]
            return None

    # Perform bisection
    index = (_start + _end) // 2
    if element < iterable[index]:  # pyright: ignore[reportOperatorIssue]
        return binary_search(element, iterable, _start=_start, _end=index - 1)
    elif element > iterable[index]:  # pyright: ignore[reportOperatorIssue]
        return binary_search(element, iterable, _start=index + 1, _end=_end)
    else:
        return index


def _read_file_chunk(file: TextIO, chunksize: int) -> str:
    """Read a chunk starting from `chunksize` before file pointer and up to current file pointer.

    If `chunksize` is larger than the current file pointer, the file is read from the beginning.
    Returns the read content in reverse order and moves the file pointer to where the content starts.
    Reverse order is used, as it will be mostly faster to search for newlines,
    especially if there are many lines in a given chunk.
    """
    mov = file.tell() - max(file.tell() - chunksize, 0)
    file.seek(file.tell() - mov)
    reversed_content = file.read(mov)[::-1]
    file.seek(file.tell() - mov)
    return reversed_content


def reverse_line_iterator(file: TextIO, chunksize: int = DEFAULT_BUFFER_SIZE, linesep: str = "\n") -> Generator[str, None, None]:
    """Similar to file.readlines(), but lazily returns lines in reverse order.

    Will move file pointer (file.tell()) throughout execution, so be careful.
    When done, file pointer will be 0. This function is especially useful for large files,
    as it will never take up more memory that size of largest line + chunksize.
    Raises an OSError on Windows, as this function currently is not supported on Windows due
    to fuckery in how line seperators are read.
    """
    if OS.is_windows:
        raise UnsupportedOS("reverse_line_iterator is not supported on Windows")
    if len(linesep) != 1:
        raise ValueError("reverse_line_iterator only supports line seperators of length 1")

    # Go to end of file and read first chunk
    file.seek(0, os.SEEK_END)
    reversed_content = _read_file_chunk(file, chunksize)
    reversed_contents = list()
    while True:
        try:
            # Try finding the next newline
            idx = reversed_content.index(linesep, 1)
            # Yield everything up to the newline (as the content is reversed)
            yield_, reversed_content = reversed_content[:idx], reversed_content[idx:]
            reversed_contents.append(yield_)
            yield "".join(reversed_contents)[::-1]
            reversed_contents = list()
        except ValueError:
            # No newline was found, so read a new chunk
            reversed_contents.append(reversed_content)
            reversed_content = _read_file_chunk(file, chunksize)
            if not reversed_content:
                break

    yield "".join(reversed_contents)[::-1]


def except_keys(d: dict[_T, Any], except_keys: Iterable[_T]) -> dict[_T, Any]:  # pyright: ignore[reportExplicitAny]
    """Return a shallow copy of the given dictionary, but with given keys removed."""
    except_keys = set(except_keys)
    return {kw: v for kw, v in d.items() if kw not in except_keys}


class HardwareInfo:
    """Information on the available hardware."""

    # Name of the CPU
    cpu: str = cpuinfo.get_cpu_info()["brand_raw"]
    # How many CPU sockets there are on the system
    # Only works on Linux, otherwise None
    sockets = int(subprocess.check_output('cat /proc/cpuinfo | grep "physical id" | sort -u | wc -l', shell=True)) if OS.is_linux else None
    # Total threads available across all CPU sockets
    threads = os.cpu_count()
    # Total system memory in bytes
    memory = psutil.virtual_memory().total
    # Available gpu
    # Requires torch, otherwise None
    gpus = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if _has_torch and torch.cuda.is_available() else None  # pyright: ignore[reportPossiblyUnboundVariable]

    @classmethod
    def string(cls) -> str:
        """Pretty string-representation of hardware."""
        lines = [
            f"CPU:     {cls.cpu}",
            f"Sockets: {cls.sockets}" if cls.sockets else None,
            f"Threads: {cls.threads:,}" if cls.threads else None,
            f"RAM:     {cls.memory / 2**30:,.2f} GiB",
            f"GPU(s):  {cls.gpus[0]}" if cls.gpus else None,
            *[f"         {gpu}" for gpu in (cls.gpus[1:] if cls.gpus is not None and len(cls.gpus) > 1 else [])],
        ]
        return os.linesep.join(line for line in lines if line)


# Placed down here to prevent issues with circular imports.
from .__version__ import __version__
from .format import RichString, Table
from .job_parser import ArgumentTypes, ConfigError, Flag, JobDescription, JobParser, OptionalArg, ParserError, RequiredArg
from .logging import Logger, LoggingException, LogLevels, log
from .pretty_json import pretty_json
from .serialization import UniversalJsonModel
from .ticktock import TT, Profile, TickTock, TickTockException, TimeUnits

__all__ = (
    "OS",
    "TT",
    "ArgumentTypes",
    "ConfigError",
    "EnvVars",
    "Flag",
    "HardwareInfo",
    "JobDescription",
    "JobParser",
    "LogLevels",
    "Logger",
    "LoggingException",
    "OptionalArg",
    "ParserError",
    "Profile",
    "RequiredArg",
    "RichString",
    "Table",
    "TickTock",
    "TickTockException",
    "TimeUnits",
    "UniversalJsonModel",
    "UnsupportedOS",
    "__version__",
    "array_ptr",
    "binary_search",
    "except_keys",
    "get_repo",
    "get_timestamp",
    "get_timestamp_for_files",
    "log",
    "pretty_json",
    "reverse_line_iterator",
    "split_path",
)
