"""Functions for attempting imports which may or may not be available at runtime."""


def import_torch():
    """Attempt a import of torch. If found, torch is returned, otherwise None is returned."""
    try:
        import torch  # noqa: PLC0415

        return torch
    except ModuleNotFoundError:
        return None


def import_git():
    """Attempt a import of git. If successful, git is returned, otherwise None is returned."""
    try:
        import git  # noqa: PLC0415

        return git
    except ImportError:  # The Python git library should always be available, but git may not be available on the system
        return None
