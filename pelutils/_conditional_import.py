def import_torch():
    """Attempt a import of torch. If found, torch is returned, otherwise None."""
    try:
        import torch  # noqa: PLC0415

        return torch
    except ModuleNotFoundError:
        return None
