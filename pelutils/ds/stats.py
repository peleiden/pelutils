from __future__ import annotations
from typing import Iterable, Callable

import numpy as np

from . import _import_error

try:
    from scipy import stats
except ModuleNotFoundError as e:
    raise _import_error from e


def z(alpha=0.05, two_sided=True, distribution=stats.norm(0, 1)):
    """ Get z value for a given significance level """
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be between 0 and 1, not %s" % alpha)
    if two_sided:
        return distribution.ppf(1 - alpha / 2)
    else:
        return distribution.ppf(1 - alpha)

def corr_ci(x: Iterable, y: Iterable, alpha=0.05, output: Callable=None):
    """
    A convenience function for getting a pearson correlation + confidence interval of it.
    Uses the method often called Fisher's z transformation: https://en.wikipedia.org/wiki/Fisher_transformation
    which is only exact if X, Y follow bivariate normal

    x, y:  Data iterables to compare

    alpha: Significance level. 0.05 by default
    output: A function to use to output a string with the information. Could be `log` or `print`

    Returns
    float: Pearson's correlation coefficient
    float, float: The lower and upper bound of confidence intervals
    float : The corresponding p value

    Inspired by https://zhiyzuo.github.io/Pearson-Correlation-CI-in-Python/
    """

    r, p = stats.pearsonr(x, y)
    r_z  = np.arctanh(r)
    se   = 1 / np.sqrt(x.size - 3)

    z          = stats.norm.ppf(1 - alpha/2)
    lo_z, hi_z = r_z + np.array((-1, 1)) * z * se
    lo, hi     = np.tanh((lo_z, hi_z))

    if output is not None:
        output(f"\t Correlation {r:.3f} in [{lo:.3f}, {hi:.3f}], with p={p:.3f}")
    return r, lo, hi, p
