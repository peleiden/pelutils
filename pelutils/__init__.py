from __future__ import annotations
import os
import ctypes
import random
from datetime import datetime
from typing import Iterable, TypeVar

import git
import numpy as np
try:
    import torch
    _has_torch = True
except:
    _has_torch = False


T = TypeVar("T")


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

def get_timestamp(for_file = False, include_micros = False) -> str:
    """
    Returns a time stamp
    If for_file is true, it can be used to save files and: YYYY-MM-DD_HH-mm-SS
    Else the timestamp will be YYYY-MM-DD HH:mm:SS:milliseconds
    Set include_micros to include microseconds in time stamp (only if for_file is false)
    Returns a time stamp for current time either in datetime format or, if for_file, in YYYY-MM-DD_HH-MM-SS
    """
    d_string = str(datetime.now())
    if not include_micros:
        d_string = d_string[:-3]
    if for_file:
        d_string = "-".join(d_string.split(".")[0].split(":")).replace(" ", "_")
    return d_string

def thousand_seps(numstr: str | float | int) -> str:
    """ Formats a number using thousand seperators """
    decs = str(numstr)
    rest = ""
    if "." in decs:
        rest = decs[decs.index("."):]
        decs = decs[:decs.index(".")]
    for i in range(len(decs)-3, 0, -3):
        decs = decs[:i] + "," + decs[i:]
    return decs + rest

def throws(exc_type: type, fun: Callable, *args, **kwargs) -> bool:
    """ Check if fun(*args, **kwargs) throws an error of a given type """
    try:
        fun(*args, **kwargs)
        return False
    except exc_type:
        return True

class EnvVars:
    """
    Execute a piece of code with certain environment variables
    Example: Disabling multithreading in tesseract
    ```
    with EnvVars(OMP_THREAD_LIMIT=1):
        # Tesseract code here
    ```
    Any existing environment variables are restored, and newly added are removed after exiting with block
    """

    _origs: dict

    def __init__(self, **env_vars):
        self._vars = env_vars

    def __enter__(self):
        self._origs = dict()
        for var, value in self._vars.items():
            self._origs[var] = os.environ.get(var)
            os.environ[var] = str(value)

    def __exit__(self, *args):
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

def binary_search(element: T, iterable: Iterable[T], *, _start=0, _end=-1) -> int | None:
    """ Get the index of element in iterable using binary search
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


# To allow imports directly from utils #
# Currently to be placed lower because get_timestamp is needed by logger #
from .logger import *
from .logger import _Logger
log: _Logger  # Make sure type hinting works when importing global instances
from .parser import *
from .ticktock import *
TT: TickTock
from .datastorage import *
from .tests import *
from .format import *
from .jsonl import *
