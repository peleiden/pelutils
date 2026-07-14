import os
from pathlib import Path

import git


def git_repo_info(path: str | Path | None = None) -> tuple[Path, str] | tuple[None, None]:
    """Return absolute path of git repository and commit SHA.

    Searches for repo by searching upwards from given directory (if None: uses working dir).
    If it cannot find a repository, it returns (None, None).
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
            return Path(cdir).resolve(), str(repo.head.commit)
        except git.InvalidGitRepositoryError:
            pass
        pdir = os.path.dirname(cdir)

    return None, None
