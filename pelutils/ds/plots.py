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
    """ Update matplotlib parameters - utility function for preventing always having to look it up """
    plt.rcParams.update(rc_params)

# Colours
base_colours: list[str] = list(mcolour.BASE_COLORS)  # 8 colours
tab_colours:  list[str] = list(mcolour.TABLEAU_COLORS)  # 10 colours
colours:      list[str] = tab_colours[:-2] + base_colours[:-1]  # 15 unique matplotlib colours

# Common figure sizes
figsize_std  = (15, 10)
figsize_wide = (22, 10)

def moving_avg(
    x: np.ndarray,
    y: np.ndarray | None = None, *,
    neighbors            = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """ Calculates the moving average assuming even spacing
    If one array of size n is given, it is assumed to run from 0 to n-1 on the x axis
    If two are given, the first are the x axis coordinates
    Returns x and y coordinate arrays of same size """
    if y is None:
        y = x
        x = np.arange(x.size)
    x = x[neighbors:-neighbors]
    kernel = np.arange(1, 2*neighbors+2)
    kernel[-neighbors:] = np.arange(neighbors, 0, -1)
    kernel = kernel / kernel.sum()
    rolling = np.convolve(y, kernel, mode="valid")
    return x, rolling

def exp_moving_avg(
    x: np.ndarray,
    y: np.ndarray | None = None, *,
    alpha                = 0.2,
    reverse              = False,
) -> np.ndarray:
    """ Calculates the exponential moving average
    alpha is a smoothing factor between 0 and 1 - the lower the value, the smoother the curve
    Returns two arrays of same size as x
    This function optionally takes y as `moving_avg` """
    if y is None:
        y = x
        x = np.arange(x.size)
    if reverse:
        y = y[::-1]

    exp = np.empty(y.size)
    for i in range(y.size):
        if i:
            exp[i] = alpha * y[i] + (1 - alpha) * exp[i-1]
        else:
            exp[i] = y[i]
    return x, exp if not reverse else exp[::-1]

def double_moving_avg(
    x: np.ndarray,
    y: np.ndarray | None = None, *,
    inner_neighbors      =   1,
    outer_neighbors      =  12,
    samples              = 300,
) -> tuple[np.ndarray, np.ndarray]:
    """ Moving avg. function that produces smoother curves than normal moving avg.
    Also handles uneven data spacing better, and produces smoothed values for the entire span.
    This function optionally takes y as `moving_avg`.
    If both x and y are given, x must be sorted in ascending order.
    inner_neighbors: How many neighbors to use for the initial moving average.
    outer_neighbors: How many neighbors to use for for the second moving average.
    samples: How many points to sample the moving avg. at. """
    if y is None:
        y = x
        x = np.arange(x.size)
    x = np.pad(x, pad_width=inner_neighbors)
    y = np.array([*[y[0]]*inner_neighbors, *y, *[y[-1]]*inner_neighbors])
    x, y = moving_avg(x, y, neighbors=inner_neighbors)
    # Sampled point along x axis
    extra_sample = outer_neighbors / samples
    # Sample points along x axis
    xx = np.linspace(
        x[0] - extra_sample * (x[-1]-x[0]),
        x[-1] + extra_sample * (x[-1]-x[0]),
        samples + 2 * outer_neighbors,
    )
    # Interpolated points
    yy = np.zeros_like(xx)
    yy[:outer_neighbors] = y[0]
    yy[-outer_neighbors:] = y[-1]

    # Perform interpolation
    x_index = 0
    for k, interp_x in enumerate(xx[outer_neighbors:outer_neighbors+samples], start=outer_neighbors):
        while interp_x >= x[x_index+1]:
            x_index += 1
        a = (y[x_index+1] - y[x_index]) / (x[x_index+1] - x[x_index])
        b = y[x_index] - a * x[x_index]
        yy[k] += (a * interp_x + b)

    return moving_avg(xx, yy, neighbors=outer_neighbors)

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
    y, edges = np.histogram(data, bins=bins, density=density)
    x = (edges[1:] + edges[:-1]) / 2
    if ignore_zeros:
        x, y = x[y>0], y[y>0]
    return x, y
