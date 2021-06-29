from __future__ import annotations
from typing import Any, Callable, Iterable

from . import _import_error
try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolour
    from scipy import stats
except ModuleNotFoundError as e:
    raise _import_error from e
import numpy as np

# All rc params are available here
# https://matplotlib.org/3.2.1/tutorials/introductory/customizing.html#customizing-with-matplotlibrc-files
rc_params       = { "font.size": 26, "legend.fontsize": 24, "legend.framealpha": 1, "legend.edgecolor": (0, 0, 0, 1) }
rc_params_small = { **rc_params, "font.size": 22, "legend.fontsize": 20 }  # Same but with smaller font

def update_rc_params(rc_params: dict[str, Any]):
    plt.rcParams.update(rc_params)

# Colours
base_colours: list[str] = list(mcolour.BASE_COLORS)  # 8 colours
tab_colours:  list[str] = list(mcolour.TABLEAU_COLORS)  # 10 colours
colours:      list[str] = tab_colours[:-2] + base_colours[:-1]  # 15 unique matplotlib colours

# Common figure sizes
figsize_std  = (15, 10)
figsize_wide = (22, 10)

# Utility functions for histograms
def linear_binning(x: Iterable, bins: int) -> np.ndarray:
    """ Standard linear binning """
    return np.linspace(min(x), max(x), bins)

def log_binning(x: Iterable, bins: int) -> np.ndarray:
    """ Logarithmic binning """
    return np.logspace(np.log10(min(x)), np.log10(max(x)), bins)

def normal_binning(x: Iterable, bins: int) -> np.ndarray:
    """ Creates bins that fits nicely to a normally distributed variable
    Bins are smaller close to the mean of x """
    dist = stats.norm(np.mean(x), 3*np.std(x))
    p = min(dist.cdf(min(x)), 1-dist.cdf(max(x)))
    uniform_spacing = np.linspace(p, 1-p, bins)
    return dist.ppf(uniform_spacing)

def get_bins(
    data:         Iterable,
    binning_fn:   Callable[[Iterable, int], Iterable] = linear_binning,
    bins:         int  = 25,
    density:      bool = True,
    ignore_zeros: bool = False,
):
    """ Create bins for plotting a line histogram. Simplest usage is plt.plot(*get_bins(data)) """
    bins = binning_fn(data, bins+1)
    y, edges = np.histogram(data, bins=bins, density=True)
    x = (edges[1:] + edges[:-1]) / 2
    if ignore_zeros:
        x, y = x[y>0], y[y>0]
    return x, y
