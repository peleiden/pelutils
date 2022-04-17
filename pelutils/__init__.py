from __future__ import annotations
from collections.abc import Sequence
from datetime import datetime
from io import DEFAULT_BUFFER_SIZE
from typing import Generator, TextIO, TypeVar
import os
import ctypes
import random

import git
import numpy as np
try:
    import torch
    _has_torch = True
except:
    _has_torch = False


_T = TypeVar("_T")

class UnsupportedOS(Exception):
    pass

def set_seeds(seed: int=0):
    np.random.seed(seed)
    random.seed(seed)
    if _has_torch:
        # https://pytorch.org/docs/stable/notes/randomness.html
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

def get_repo(path: str | None=None) -> tuple[str | None, str | None]:
    """
    Returns absolute path of git repository and commit SHA
    Searches for repo by searching upwards from given directory (if None: uses working dir).
    If it cannot find a repository, returns (None, None)
    """
    if path is None:
        path = os.getcwd()
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

def get_timestamp(*, with_date=True) -> str:
    """ Returns a timestamp formatted as YYYY-MM-DD HH:mm:SS.ms. """
    tstr = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    if not with_date:
        tstr = tstr[11:]
    return tstr

def thousands_seperators(num: float | int, decimal_seperator=".") -> str:
    """ Formats a number using thousand seperators """
    if decimal_seperator not in { ".", "," }:
        raise ValueError("'%s' is not a valid decimal seperator. Use '.' or ','" % decimal_seperator)

    num = str(num)
    is_negative = num.startswith("-")
    if is_negative:
        num = num[1:]
    tsep = "," if decimal_seperator == "." else "."

    rest = ""
    if "." in num:
        rest = decimal_seperator + num[num.index(".")+1:]
        num = num[:num.index(".")]
    for i in range(len(num)-3, 0, -3):
        num = num[:i] + tsep + num[i:]
    if is_negative:
        num = "-" + num

    return num + rest

def raises(exc_type: type, fun: Callable, *args, **kwargs) -> bool:
    """ Check if fun(*args, **kwargs) throws an error of a given type. """
    try:
        fun(*args, **kwargs)
        return False
    except exc_type:
        return True
    except:
        return False

class EnvVars:
    """ Execute a piece of code with certain environment variables.
    ALl environment variables are restored after with block.
    Example: Disabling multithreading in tesseract:
    ```
    with EnvVars(OMP_THREAD_LIMIT=1):
        # Tesseract code here
    ```
    Any existing environment variables are restored, and newly added are removed after exiting with block. """

    _origs: dict

    def __init__(self, **env_vars):
        self._vars = env_vars

    def __enter__(self):
        self._origs = dict()
        for var, value in self._vars.items():
            self._origs[var] = os.environ.get(var)
            os.environ[var] = str(value)

    def __exit__(self, *__):
        for var, value in self._origs.items():
            if value is None:
                del os.environ[var]
            else:
                os.environ[var] = value

def c_ptr(arr: np.ndarray | torch.Tensor) -> ctypes.c_void_p:
    """
    Returns a c pointer that can be used to import a contiguous numpy array or torch tensor into a c function
    Returns null pointer if unable to resolve pointer, including if arr is None
    """
    if isinstance(arr, np.ndarray):
        return ctypes.c_void_p(arr.ctypes.data)
    elif _has_torch and isinstance(arr, torch.Tensor):
        return ctypes.c_void_p(arr.data_ptr())
    return ctypes.c_void_p(None)

def split_path(path: str) -> list[str]:
    """ Splits a path into components """
    return os.path.normpath(path).split(os.sep)

def binary_search(element: _T, iterable: Sequence[_T], *, _start=0, _end=-1) -> int | None:
    """ Get the index of element in sequence using binary search
    Assumes iterable is sorted in ascending order
    Returns None if the element is not found """
    if _end == -1:  # Entered on first call
        _end = len(iterable)
        # Make sure element actually exists in array
        if not iterable[0] <= element <= iterable[-1]:
            return None

    # Perform bisection
    index = (_start + _end) // 2
    if element < iterable[index]:
        return binary_search(element, iterable, _start=_start, _end=index-1)
    elif element > iterable[index]:
        return binary_search(element, iterable, _start=index+1, _end=_end)
    else:
        return index

def is_windows() -> bool:
    """ Checks if running on a Windows machine. """
    return os.name == "nt"

def _read_file_chunk(file: TextIO, chunksize: int) -> str:
    """ Reads a chunk starting from `chunksize` before file pointer and up to current file pointer
    If `chunksize` is larger than the current file pointer, the file is read from the beginning
    Returns the read content in reverse order and moves the file pointer to where the content starts
    Reverse order is used, as it will be mostly faster to search for newlines,
    especially if there are many lines in a given chunk """
    mov = file.tell() - max(file.tell()-chunksize, 0)
    file.seek(file.tell()-mov)
    reversed_content = file.read(mov)[::-1]
    file.seek(file.tell()-mov)
    return reversed_content

def reverse_line_iterator(file: TextIO, chunksize=DEFAULT_BUFFER_SIZE, linesep="\n") -> Generator[str, None, None]:
    """ Similar to file.readlines(), but lazily returns lines in reverse order.
    Will move file pointer (file.tell()) throughout execution, so be careful.
    When done, file pointer will be 0. This function is especially useful for large files,
    as it will never take up more memory that size of largest line + chunksize.
    Raises an OSError on Windows, as this function currently is not supported on Windows due
    to fuckery in how line seperators are read. """

    if is_windows():
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

def except_keys(d: dict[_T, Any], except_keys: Iterable[_T]) -> dict[_T, Any]:
    """ Returns the given dictionary, but with given keys removed """
    except_keys = set(except_keys)
    return { kw: v for kw, v in d.items() if kw not in except_keys }

# To allow imports directly from utils
# Placed down here to prevent issues with circular imports
from .__version__ import __version__
from .logging import *
log: Logger  # Make sure type hinting works when importing global instances
from .parser import *
from .ticktock import *
TT: TickTock
from .datastorage import *
from .tests import *
from .format import *
from .jsonl import *
