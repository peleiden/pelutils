import os
from pathlib import Path

from pelutils.misc._conditional_import import import_git

git = import_git()


def git_repo_info(path: str | Path | None = None) -> tuple[Path, str | None] | tuple[None, None]:
    """Return the working tree root and current commit SHA of a git repository.

    The repository is found by searching upwards from `path`, or from the working directory
    if `path` is None. If no repository with a working tree is found, or git is unavailable,
    ``(None, None)`` is returned. The commit SHA is None if the repository has no commits.
    """
    if git is None:
        return None, None
    if path is None:
        path = os.getcwd()
    try:
        # Resolve symlinks first, as git does
        repo = git.Repo(Path(path).resolve(), search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        return None, None
    with repo:
        if repo.working_tree_dir is None:
            # Bare repository
            return None, None
        try:
            commit = repo.head.commit.hexsha
        except ValueError:
            # HEAD points to a branch without commits
            commit = None
        return Path(repo.working_tree_dir).resolve(), commit
