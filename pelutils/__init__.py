import os
import random
from datetime import datetime
from typing import Tuple

import git
import numpy as np
try:
    import torch
    _has_torch = True
except ModuleNotFoundError:
    _has_torch = False


def set_seeds(seed: int = 0):
    np.random.seed(seed)
    random.seed(seed)
    if _has_torch:
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

def get_repo(path: str=None) -> Tuple[str, str]:
    """
    Returns full path of git repository and commit SHA
    Searches for repo by searching upwards from given directory (if None: uses working dir).
    If it cannot find a repository, it raises a git.InvalidGitRepositoryError
    """
    if path is None:
        path = os.getcwd()
    cdir = os.path.join(path, ".")
    pdir = os.path.dirname(cdir)
    while cdir != pdir:
        cdir = pdir
        try:  # Check if repository
            repo = git.Repo(cdir)
            return cdir, str(repo.head.commit)
        except git.InvalidGitRepositoryError:
            pass
        pdir = os.path.dirname(cdir)
    else:  # Raise error if no repo was found
        raise git.InvalidGitRepositoryError("Unable to find git repository from %s" % path)

def get_timestamp(for_file: bool = False, include_micros = False) -> str:
    """
    Returns a time stamp
    If for_file is true, it can be used to save files and: YYYY-MM-DD_HH-mm-SS
    Else the timestamp will be YYYY-MM-DD HH:mm:SS:milliseconds
    Set include_micros to include microseconds in time stamp (only if for_file is false)
    Returns a time stamp for current time either in datetime format or, if for_file, in YYYY-MM-DD_HH-MM-SS
    """
    d_string = str(datetime.now()) if include_micros else str(datetime.now())[:-3]
    if for_file:
        d_string = "-".join(d_string.split(".")[0].split(":")).replace(" ", "_")
    return d_string

def thousand_seps(numstr: str or float or int) -> str:
    decs = str(numstr)
    rest = ""
    if "." in decs:
        rest = decs[decs.index("."):]
        decs = decs[:decs.index(".")]
    for i in range(len(decs)-3, 0, -3):
        decs = decs[:i] + "," + decs[i:]
    return decs + rest

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


# To allow imports directly from utils #
# Currently to be placed lower because get_timestamp is needed by logger #
from .logger import *
from .parse import *
from .ticktock import *
from .datahandling import *
