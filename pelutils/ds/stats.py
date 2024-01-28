from __future__ import annotations
from typing import Iterable

import numpy as np
from scipy import stats


def z(alpha=0.05, two_sided=True, distribution=stats.norm()) -> np.float64:
    """ Get z value for a given significance level """
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be between 0 and 1, not %s" % alpha)
    if two_sided:
        return distribution.ppf(1 - alpha / 2)
    else:
        return distribution.ppf(1 - alpha)

def corr_ci(x: Iterable, y: Iterable, *, alpha=0.05, return_string=False) -> tuple[float, float, float, float] | str:
    """ A convenience function for getting a pearson correlation + confidence interval of it.
    Uses the method often called Fisher's z transformation: https://en.wikipedia.org/wiki/Fisher_transformation.
    which is only exact if X, Y follow bivariate normal.

    x, y:  Data iterables to compare. Should of equal length.

    alpha: Significance level. 0.05 by default.
    return_string: If true, the function returns a string with the information for easy printing.

    Returns
    float: Pearson's correlation coefficient.
    float: Lower bound of confidence interval for given alpha.
    float: Upper bound of confidence interval for given alpha.
    float: The corresponding p value.

    Inspired by https://zhiyzuo.github.io/Pearson-Correlation-CI-in-Python/ """

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
