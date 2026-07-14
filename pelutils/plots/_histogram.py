from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt
from scipy import stats

from pelutils.types import FloatArray, IntArray


def linear_binning(x: npt.ArrayLike, bins: int) -> FloatArray:
    """Calculate linear binning for an array."""
    x = np.asarray(x)
    return np.linspace(x.min(), x.max(), bins)


def log_binning(x: npt.ArrayLike, bins: int) -> FloatArray:
    """Calculate logarithmic binning for an array, meaning more bins close to zero."""
    x = np.asarray(x)
    return np.geomspace(x.min(), x.max(), bins)


def normal_binning(x: npt.ArrayLike, bins: int, scale: float = 3) -> FloatArray:
    """Calculate bins that work well for normal-ish distributed data, meaning more bins closer to the mean of x.

    `scale` determines how spread out the spacing is. The default value works pretty well in most cases.
    """
    x = np.asarray(x)
    dist = stats.norm(x.mean(), scale * x.std())
    p = min(dist.cdf(min(x)), 1 - dist.cdf(max(x)))
    uniform_spacing = np.linspace(p, 1 - p, bins)
    return dist.ppf(uniform_spacing)


def histogram(
    data: npt.ArrayLike,
    binning_fn: Callable[[npt.ArrayLike, int], FloatArray] = linear_binning,
    bins: int = 25,
    density: bool = True,
    ignore_zeros: bool = False,  # Be careful about this one, but it can be practical with log scales
) -> tuple[FloatArray, FloatArray | IntArray]:
    """Create bins for plotting a line histogram. Simplest usage is ``plt.plot(*histogram(data))``."""
    found_bins = np.array(binning_fn(data, bins + 1))
    y, edges = np.histogram(data, bins=found_bins, density=density)
    x = (edges[1:] + edges[:-1]) / 2
    if ignore_zeros:
        keep = y > 0
        x, y = x[keep], y[keep]
    return x, y
