from __future__ import annotations

import os
from argparse import ArgumentParser

import git
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

from pelutils import get_repo
from pelutils.ds.plots import Figure, get_dateticks

_default_extensions = ", ".join((
    ".py", ".pyw",
    ".c", ".cpp", ".cc", ".h", ".hpp",
    ".tex",
    ".html", ".css", ".js", ".jsx", ".ts",
    ".java", ".kt", ".dart", ".swift",
    ".rs", ".go",
    ".r", ".m",
    ".sh", ".zsh", ".bash",
))

def _count(repo: git.Repo, branch: git.Head, exts: list[str]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Count lines of all files recursively in the current working directory.

    Return an array of commit epoch times and a dict mapping file extensions to line counts
    """
    commits = list(reversed(list(repo.iter_commits())))  # List of commit from oldest to newest
    times = np.array([c.committed_date for c in commits])
    lines = { ext: np.zeros_like(times) for ext in exts }
    try:
        for i, commit in enumerate(tqdm(commits)):
            try:
                repo.git.checkout(str(commit))
            except git.GitCommandError as e:
                # This error happens if there is a file that has been moved in and out of .gitignore
                # For safety, the commit is ignored
                if "error: The following untracked working tree files would be overwritten by checkout:" in str(e):
                    continue
                raise
            for path, __ in repo.index.entries:
                try:
                    ext = next(e for e in exts if path.endswith(e) and os.path.isfile(path))
                except StopIteration:
                    continue
                with open(path) as f:
                    lines[ext][i] += len([line for line in f.readlines() if line.strip()])
    finally:
        repo.git.checkout(branch)

    return times, lines

def _fuse_times(all_times: list[np.ndarray]) -> np.ndarray:
    """Merge all time arrays together into a single array that is also sorted."""
    n = sum(times.size for times in all_times)
    times = np.empty(n, dtype=int)
    idcs = [0] * len(all_times)
    for i in range(n):
        current_times = [time[idx] if idx < len(time) else float("inf") for time, idx in zip(all_times, idcs)]
        min_time = np.argmin(current_times)
        times[i] = current_times[min_time]
        idcs[min_time] += 1
    return times

def _last_initial_zero(values: np.ndarray) -> int:
    if values[0] != 0:
        return 0
    return np.where(values!=0)[0][0] - 1

def linecounter(repos: list[str], output: str, extensions: str, date_format: str, no_repo_name: bool):
    extensions = [x.strip() for x in extensions.split(",")]
    extensions = [x if x.startswith(".") else "." + x for x in extensions]
    wd = os.getcwd()
    repo_names, all_times, all_counts = list(), list(), list()
    for repo in repos:
        repo_path, __ = get_repo(repo)
        if repo_path is None:
            raise ValueError(f"{repo_path} is not a git repository")
        os.chdir(repo_path)

        try:
            repo = git.Repo()
            branch = repo.active_branch
            times, lines = _count(repo, branch, extensions)
        finally:
            # Reset repo
            repo.git.checkout(branch)

        repo_names.append(os.path.split(repo_path)[-1])
        all_times.append(times)
        all_counts.append(lines)
        os.chdir(wd)

    with Figure(output):
        for _i, (repo_name, times, counts) in enumerate(zip(repo_names, all_times, all_counts)):
            for ext, line_counts in counts.items():
                if not line_counts.any():
                    continue
                non_zero = line_counts != 0
                non_zero[_last_initial_zero(line_counts)] = 1
                lab = ext+(f" ({repo_name})" if len(repo_names) > 1 and not no_repo_name else "")
                plt.plot(times[non_zero], line_counts[non_zero], marker=".", ms=8, lw=2, label=lab)

        fused_times = _fuse_times(all_times)
        plt.xticks(*get_dateticks(fused_times, date_format=date_format))
        title = "Line count over time" + (f" ({repo_name})" if len(repo_names) == 1 and not no_repo_name else "")
        plt.title(title)
        plt.xlabel("Date of commit")
        plt.ylabel("Number of non-empty lines")
        plt.legend(loc=2)
        plt.grid()

def run():
    parser = ArgumentParser()
    parser.add_argument("repos", nargs="+")
    parser.add_argument("-o", "--output", default="linecount.png", help="Path to produce output figure to.")
    parser.add_argument("-e", "--extensions", default=_default_extensions, help="Comma seperated list of file extensions to look for.")
    parser.add_argument("-d", "--date-format", default="%y-%m-%d", help="How to format axis labels.")
    parser.add_argument("-n", "--no-repo-name", action="store_true", help="Disable repository name from the produced figure.")
    args = parser.parse_args()

    linecounter(args.repos, args.output, args.extensions, args.date_format, args.no_repo_name)

if __name__ == "__main__":
    run()
