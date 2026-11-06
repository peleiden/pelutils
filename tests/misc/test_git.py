from pathlib import Path

import pytest

import pelutils.misc._git as pelutils_git
from pelutils.misc import git_repo_info

git = pytest.importorskip("git")


def _make_repo(path: Path) -> str:
    """Create a repository with a single commit at `path` and return the commit SHA."""
    repo = git.Repo.init(path)
    (path / "file.txt").write_text("content")
    repo.index.add(["file.txt"])
    actor = git.Actor("Test", "test@example.com")
    commit = repo.index.commit("Initial commit", author=actor, committer=actor)
    repo.close()
    return commit.hexsha


def test_git_repo_info(tmp_path: Path):
    sha = _make_repo(tmp_path)
    assert git_repo_info(tmp_path) == (tmp_path.resolve(), sha)
    assert git_repo_info(str(tmp_path)) == (tmp_path.resolve(), sha)


def test_git_repo_info_searches_upwards(tmp_path: Path):
    sha = _make_repo(tmp_path)
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)
    assert git_repo_info(subdir) == (tmp_path.resolve(), sha)


def test_git_repo_info_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sha = _make_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert git_repo_info() == (tmp_path.resolve(), sha)


def test_git_repo_info_no_repo(tmp_path: Path):
    if git_repo_info(tmp_path.parent) != (None, None):
        pytest.skip("Temporary directory is inside a git repository")
    assert git_repo_info(tmp_path) == (None, None)


def test_git_repo_info_without_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _make_repo(tmp_path)
    monkeypatch.setattr(pelutils_git, "git", None)
    assert git_repo_info(tmp_path) == (None, None)


def test_git_repo_info_no_commits(tmp_path: Path):
    git.Repo.init(tmp_path).close()
    assert git_repo_info(tmp_path) == (tmp_path.resolve(), None)


def test_git_repo_info_file_path(tmp_path: Path):
    sha = _make_repo(tmp_path)
    assert git_repo_info(tmp_path / "file.txt") == (tmp_path.resolve(), sha)


def test_git_repo_info_inside_git_dir(tmp_path: Path):
    sha = _make_repo(tmp_path)
    assert git_repo_info(tmp_path / ".git" / "refs") == (tmp_path.resolve(), sha)


def test_git_repo_info_bare(tmp_path: Path):
    git.Repo.init(tmp_path, bare=True).close()
    assert git_repo_info(tmp_path) == (None, None)


def test_git_repo_info_symlink(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    sha = _make_repo(repo_dir)
    link = tmp_path / "link"
    try:
        link.symlink_to(repo_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks are not supported")
    assert git_repo_info(link) == (repo_dir.resolve(), sha)
