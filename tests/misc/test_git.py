import os
from pathlib import Path
from shutil import move

import pelutils.misc._git as pelutils_git
from pelutils.misc import git_repo_info


def test_git_repo_info():
    if ".git" in os.listdir() and pelutils_git.git is not None:
        a, b = git_repo_info()
        assert isinstance(a, Path)
        assert isinstance(b, str)

    git = pelutils_git.git

    pelutils_git.git = None
    a, b = git_repo_info()
    assert a is None
    assert b is None

    pelutils_git.git = git
    if ".git" in os.listdir():
        move(".git", ".gittmp")
        a, b = git_repo_info()
        assert a is None
        assert b is None
        move(".gittmp", ".git")
