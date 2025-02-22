from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy import stats


def z(alpha=0.05, two_sided=True, distribution=stats.norm()) -> float:  # noqa: B008
    """Get z value for a given significance level."""
    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be between 0 and 1, not {alpha}")
    if two_sided:
        return distribution.ppf(1 - alpha / 2).item()
    else:
        return distribution.ppf(1 - alpha).item()

def corr_ci(x: Iterable, y: Iterable, *, alpha=0.05, return_string=False) -> tuple[float, float, float, float] | str:
    """Convenience function for getting a pearson correlation and confidence interval of it.

    It uses the method often called Fisher's z transformation: https://en.wikipedia.org/wiki/Fisher_transformation,
    which is only exact if (X, Y) follow a bivariate normal.

    Inspired by https://zhiyzuo.github.io/Pearson-Correlation-CI-in-Python.

    Parameters
    ----------
    x, y : Iterable
        Data iterables to compare. Should of equal length and numeric.
    alpha : float, optional
        Significance level, by default 0.05.
    return_string : bool, optional
        If true, the function returns a string with the information for easy printing, by default False.

    Returns
    -------
    tuple[float, float, float, float] | str
        If return_string is not True, the four returned floats are
            - Pearson's correlation coefficient.
            - Lower bound of confidence interval for given alpha.
            - Upper bound of confidence interval for given alpha.
            - The corresponding p value.
    """  # noqa: D401
    # Convert x and y from arbitrary iterables to arrays
    if not hasattr(x, "__len__"):
        x = np.fromiter(x, float)
    if not hasattr(y, "__len__"):
        y = np.fromiter(y, float)
    x = np.array(x)
    y = np.array(y)

    r, p = stats.pearsonr(x, y)
    r_z  = np.arctanh(r)
    se   = 1 / np.sqrt(x.size - 3)

    z          = stats.norm.ppf(1 - alpha/2)
    lo_z, hi_z = r_z + np.array((-1, 1)) * z * se
    lo, hi     = np.tanh((lo_z, hi_z))

    if return_string:
        return f"Correlation {r:.3f} in [{lo:.3f}, {hi:.3f}], with p={p:.3f}"
    return r, lo, hi, p
