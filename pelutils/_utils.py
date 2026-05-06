import sys
from typing import Any


def isinstance_by_name(obj: Any, module: str, qualname: str) -> bool:  # pyright: ignore[reportExplicitAny]
    """Check whether ``obj`` is an instance of a class without importing its module.

    This is useful for libraries with optional dependencies: if the dependency
    has not been imported anywhere in the current process, ``obj`` cannot
    possibly be an instance of one of its classes, so we can skip the check
    without forcing an import.

    Parameters
    ----------
    obj
        The object whose type is being checked.
    module
        The fully qualified name of the module that defines the target class
        (e.g. ``"pandas"`` or ``"numpy"``).
    qualname
        The attribute name of the class within ``module`` (e.g. ``"Series"``
        or ``"ndarray"``). Dotted paths are not supported.

    Returns
    -------
    bool
        ``True`` if ``module`` is already loaded in :data:`sys.modules` and
        ``obj`` is an instance of ``module.qualname``; ``False`` otherwise
        (including when the module is not loaded or does not expose the
        named attribute).

    Examples
    --------
    >>> import pandas as pd
    >>> _isinstance_by_name(pd.Series([1, 2, 3]), "pandas", "Series")
    True
    >>> _isinstance_by_name([1, 2, 3], "pandas", "Series")
    False
    """
    mod = sys.modules.get(module)
    if mod is None:
        return False
    cls = getattr(mod, qualname, None)
    if not isinstance(cls, type):
        return False
    return isinstance(obj, cls)
