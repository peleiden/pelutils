from __future__ import annotations

import os
import time
from typing import Any, Callable, List, Optional, Union

import numpy as np
from . import _import_error
try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolour
    from scipy import stats
except ModuleNotFoundError as e:
    raise _import_error from e


_Array = Union[List[Union[float, int]], np.ndarray]

# 8 colours
base_colours: tuple[str] = tuple(mcolour.BASE_COLORS)
# 10 colours
tab_colours:  tuple[str] = tuple(mcolour.TABLEAU_COLORS)
# 15 unique matplotlib colours
colours:      tuple[str] = tab_colours[:-2] + base_colours[:-1]

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
    return x, exp if not reverse else np.array(exp)[::-1]

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
def linear_binning(x: _Array, bins: int) -> np.ndarray:
    """ Standard linear binning """
    return np.linspace(min(x), max(x), bins)

def log_binning(x: _Array, bins: int) -> np.ndarray:
    """ Logarithmic binning """
    return np.logspace(np.log10(min(x)), np.log10(max(x)), bins)

def normal_binning(x: _Array, bins: int) -> np.ndarray:
    """ Creates bins that fits nicely to a normally distributed variable
    Bins are smaller close to the mean of x """
    dist = stats.norm(np.mean(x), 3*np.std(x))
    p = min(dist.cdf(min(x)), 1-dist.cdf(max(x)))
    uniform_spacing = np.linspace(p, 1-p, bins)
    return dist.ppf(uniform_spacing)

def get_bins(
    data:         np.ndarray | list[float],
    binning_fn:   Callable[[_Array, int], _Array] = linear_binning,
    bins:         int  = 25,
    density:      bool = True,
    ignore_zeros: bool = False,
):
    """ Create bins for plotting a line histogram. Simplest usage is plt.plot(*get_bins(data)) """
    bins = np.array(binning_fn(data, bins+1))
    y, edges = np.histogram(data, bins=bins, density=density)
    x = (edges[1:] + edges[:-1]) / 2
    if ignore_zeros:
        x, y = x[y>0], y[y>0]
    return x, y

def get_dateticks(x: _Array, num=7, date_format="%y-%m-%d") -> tuple[np.array, list[str]]:
    """ Produces date labels for the x axis given an array of epoch times in seconds. Simple usage:
    ```py
    # x is an array of epoch times in seconds
    plt.plot(x, y)
    plt.xticks(*get_dateticks(x))
    ``` """
    if not isinstance(num, int) or num < 2:
        raise ValueError("num must int of value 2 or greater, not %s" % num)
    x = np.array(x)
    xticks = np.linspace(x.min(), x.max(), num)
    xticklabels = [time.strftime(date_format, time.gmtime(et)) for et in xticks]
    return xticks, xticklabels

class Figure:

    """ Used for more ergonomic plotting. Simple usecase:
    ```py
    with Figure("figure.png", figsize=(20, 10), fontsize=50):
        plt.plot(x, y)
        plt.title("Very large title")
        plt.grid()
    # The finished figure is saved to "figure.png"
    # All settings are reset here
    ```
    It is also possible to access the figure and axis produced by plt.subplots.
    These have type hinting, so it is for once possible to know what methods
    and attributes exist on fig and ax.
    In the example, the seaborn style is used (similar to `plt.style.use("seaborn"))`.
    ```py
    with Figure("figure.png", figsize=(20, 10), style="seaborn") as f:
        f.ax.set_title("Normal sized title")
        f.figure.add_axes(...)
    ``` """

    def __init__(
        self,
        savepath:     str, *,
        # nrow and ncol are given to plt.subplots
        # If either is larger than 1, the .ax attribute will be a numpy array
        nrow:         int  = 1,
        ncol:         int  = 1,
        tight_layout: bool = True,
        style:        Optional[str] = None,
        # Arguments below here go into mpl.rcParams
        figsize:           tuple[int, int] = (15, 10),
        dpi:               float = 200,
        fontsize:          float = 26,
        title_fontsize:    float = 0.5,   # Fraction of fontsize
        axes_ticksize:     float = 0.85,  # Fraction of fontsize
        legend_fontsize:   float = 0.85,  # Fraction of fontsize
        legend_framealpha: float = 0.8,
        legend_edgecolor:  tuple[float, float, float, float] = (0, 0, 0, 1),
        other_rc_params:   dict[str, Any] = dict(),
    ):
        self._savepath = savepath
        self._nrow = nrow
        self._ncol = ncol
        self._tight_layout = tight_layout
        self._style = style

        self._rc_params = {
            "font.size": fontsize,
            "figure.figsize": figsize,
            "figure.dpi": dpi,
            "figure.titlesize": title_fontsize * fontsize,
            "legend.fontsize": legend_fontsize * fontsize,
            "xtick.labelsize": axes_ticksize * fontsize,
            "ytick.labelsize": axes_ticksize * fontsize,
            "legend.framealpha": legend_framealpha,
            "legend.edgecolor": legend_edgecolor,
            **other_rc_params,
        }

    def __enter__(self):
        if self._style:
            plt.style.use(self._style)

        self._rc_context = plt.rc_context(self._rc_params)
        self._rc_context.__enter__()

        self.fig, self.ax = plt.subplots(self._nrow, self._ncol)
        self.fig: mpl.figure.Figure
        self.ax: mpl.axes.Axes | np.ndarray

        return self

    def __exit__(self, et, ev, tb):
        if self._tight_layout:
            plt.tight_layout()
        if not et:
            directory = os.path.split(self._savepath)[0]
            if directory:
                os.makedirs(directory, exist_ok=True)
            plt.savefig(self._savepath)
        plt.close()

        self._rc_context.__exit__(et, ev, tb)

        del self.fig, self.ax, self._rc_context
