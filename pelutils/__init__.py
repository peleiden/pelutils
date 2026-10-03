from importlib.metadata import version as _get_distribution_version

__version__ = _get_distribution_version("pelutils")

__all__ = ("__version__",)
