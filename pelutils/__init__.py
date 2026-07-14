import ctypes
import os
import subprocess
import sys
from collections.abc import Generator, Iterable, Sequence
from copy import deepcopy
from datetime import datetime
from io import DEFAULT_BUFFER_SIZE
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, TypeVar

import cpuinfo
import numpy as np
import numpy.typing as npt
import psutil

if TYPE_CHECKING:
    from .types import AnyArray


from pelutils._misc.array import array_bytes, array_ptr, unique
from pelutils._misc.conditional_import import import_git, import_torch
from pelutils._misc.platform import OS, UnsupportedOS, hardware_info
from pelutils._misc.table import Table

torch = import_torch()
git = import_git()

_T = TypeVar("_T")
_V = TypeVar("_V")


def get_repo(path: str | Path | None = None) -> tuple[str | None, str | None]:
    """Return absolute path of git repository and commit SHA.

    Searches for repo by searching upwards from given directory (if None: uses working dir).
    If it cannot find a repository, returns (None, None).
    """
    if git is None:
        return None, None
    if path is None:
        path = os.getcwd()
    path = str(path)
    cdir = os.path.join(path, ".")
    pdir = os.path.dirname(cdir)
    while cdir != pdir:
        cdir = pdir
        try:  # Check if repository
            repo = git.Repo(cdir)
            return os.path.realpath(cdir), str(repo.head.commit)
        except git.InvalidGitRepositoryError:
            pass
        pdir = os.path.dirname(cdir)

    return None, None


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


def except_keys(d: dict[_T, _V], except_keys: Iterable[_T]) -> dict[_T, _V]:
    """Return a shallow copy of the given dictionary, but with given keys removed."""
    except_keys = set(except_keys)
    return {kw: v for kw, v in d.items() if kw not in except_keys}


# Placed down here to prevent issues with circular imports.
from .__version__ import __version__
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
    "Flag",
    "JobDescription",
    "JobParser",
    "LogLevels",
    "Logger",
    "LoggingException",
    "OptionalArg",
    "ParserError",
    "Profile",
    "RequiredArg",
    "Table",
    "TickTock",
    "TickTockException",
    "TimeUnits",
    "UniversalJsonModel",
    "UnsupportedOS",
    "__version__",
    "array_bytes",
    "array_ptr",
    "except_keys",
    "get_repo",
    "hardware_info",
    "log",
    "pretty_json",
    "reverse_line_iterator",
    "unique",
)
