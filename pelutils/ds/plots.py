from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, List, Union

import matplotlib.colors as mcolour
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

_Array = Union[List[Union[float, int]], np.ndarray]

# 8 colours
base_colours: tuple[str] = tuple(mcolour.BASE_COLORS)
# 10 colours
tab_colours:  tuple[str] = tuple(mcolour.TABLEAU_COLORS)
# 15 unique matplotlib colours
colours:      tuple[str] = tab_colours[:-2] + base_colours[:-1]

def moving_avg(
    x: _Array,
    y: _Array | None = None, *,
    neighbors: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate the moving average assuming even spacing.

    If one array of size n is given, it is assumed to run from 0 to n-1 on the x axis.
    If two are given, the first are the x axis coordinates.
    Returns x and y coordinate arrays of same size.
    """
    x = np.array(x)
    if y is None:
        y = x
        x = np.arange(x.size)
    else:
        y = np.array(y)
    x = x[neighbors:-neighbors]
    kernel = np.arange(1, 2*neighbors+2)
    kernel[-neighbors:] = np.arange(neighbors, 0, -1)
    kernel = kernel / kernel.sum()
    rolling = np.convolve(y, kernel, mode="valid")
    return x, rolling

def exp_moving_avg(
    x: _Array,
    y: _Array | None = None, *,
    alpha: float = 0.2,
    reverse: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate the exponential moving average.

    alpha is a smoothing factor between 0 and 1. The lower the value, the smoother the curve.

    Two arrays (containing x values and corresponding smoothed y values) of same size as x are returned.
    This function optionally takes y similar to `moving_avg`.
    """
    x = np.array(x)
    if y is None:
        y = x
        x = np.arange(x.size)
    else:
        y = np.array(y)
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
    x: _Array,
    y: _Array | None = None, *,
    inner_neighbors: int = 1,
    outer_neighbors: int = 12,
    samples: int = 300,
) -> tuple[np.ndarray, np.ndarray]:
    """Moving average function that produces smoother curves than normal moving average.

    This function handles unevenly spaced data better and produces smoothed values for the entire span.
    It optionally takes y as `moving_avg`.
    If both x and y are given, x must be sorted in ascending order.
    inner_neighbors: How many neighbors to use for the initial moving average.
    outer_neighbors: How many neighbors to use for for the second moving average.
    samples: How many points to sample the moving average at.
    """  # noqa: D401
    x = np.array(x)
    if y is None:
        y = x
        x = np.arange(x.size)
    else:
        y = np.array(y)
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
    """Calculate linear binning for an array."""
    return np.linspace(min(x), max(x), bins)

def log_binning(x: _Array, bins: int) -> np.ndarray:
    """Calculate logarithmic binning for an array, meaning more bins close to zero."""
    return np.geomspace(min(x), max(x), bins)

def normal_binning(x: _Array, bins: int) -> np.ndarray:
    """Calculate bins that work well for normal-ish distributed data, meaning more bins closer to the mean of x."""
    dist = stats.norm(np.mean(x), 3*np.std(x))
    p = min(dist.cdf(min(x)), 1-dist.cdf(max(x)))
    uniform_spacing = np.linspace(p, 1-p, bins)
    return dist.ppf(uniform_spacing)

def histogram(
    data:         np.ndarray | list[float],
    binning_fn:   Callable[[_Array, int], _Array] = linear_binning,
    bins:         int  = 25,
    density:      bool = True,
    ignore_zeros: bool = False,  # Be careful about this one, but it can be practical with log scales
):
    """Create bins for plotting a line histogram. Simplest usage is plt.plot(*histogram(data))."""
    bins = np.array(binning_fn(data, bins+1))
    y, edges = np.histogram(data, bins=bins, density=density)
    x = (edges[1:] + edges[:-1]) / 2
    if ignore_zeros:
        keep = y > 0
        x, y = x[keep], y[keep]
    return x, y

def get_dateticks(x: _Array, num=6, date_format="%b %d") -> tuple[np.ndarray, list[str]]:
    """Produce date labels for the x axis given an array of epoch times in seconds.

    Example
    -------
    ```py
    # x is an array of epoch times in seconds
    plt.plot(x, y)
    plt.xticks(*get_dateticks(x))
    ```
    """
    if not isinstance(num, int) or num < 2:
        raise ValueError(f"num must int of value 2 or greater, not {num}")
    x = np.array(x)
    xticks = np.linspace(x.min(), x.max(), num)
    xticklabels = [time.strftime(date_format, time.localtime(et)) for et in xticks]
    return xticks, xticklabels

class Figure:
    """Ergonomic plotting with matplotlib.

    Example
    -------
    ```py
    with Figure("figure.png", figsize=(20, 10), fontsize=50):
        plt.plot(x, y)
        plt.title("Very large title")
        plt.grid()
    # The finished figure is saved to "figure.png"
    # All settings are reset here
    ```
    """

    def __init__(
        self,
        savepath:     str | Path, *,
        tight_layout: bool = True,
        style:        str | None = None,
        # Arguments below here go into mpl.rcParams
        figsize:           tuple[float, float] = (15, 10),
        dpi:               float = 150,
        fontsize:          float = 26,
        title_fontsize:    float = 0.5,   # Relative to fontsize
        ticksize:          float = 0.85,  # Fraction of fontsize
        labelsize:         float = 1,     # Fraction of fontsize
        legend_fontsize:   float = 0.85,  # Fraction of fontsize
        legend_framealpha: float = 0.8,
        legend_edgecolor:  tuple[float, float, float, float] = (0, 0, 0, 1),
        other_rc_params:   dict[str, Any] = None,
    ):
        if other_rc_params is None:
            other_rc_params = dict()
        self._savepath = Path(savepath)
        self._tight_layout = tight_layout
        self._style = style

        self._rc_params = {
            "font.size": fontsize,
            "figure.figsize": figsize,
            "figure.dpi": dpi,
            "figure.titlesize": title_fontsize * fontsize,
            "legend.fontsize": legend_fontsize * fontsize,
            "xtick.labelsize": ticksize * fontsize,
            "ytick.labelsize": ticksize * fontsize,
            "axes.labelsize": labelsize * fontsize,
            "legend.framealpha": legend_framealpha,
            "legend.edgecolor": legend_edgecolor,
            **other_rc_params,
        }

    def __enter__(self):
        if self._style:
            plt.style.use(self._style)

        self._rc_context = plt.rc_context(self._rc_params)
        self._rc_context.__enter__()

    def __exit__(self, et, ev, tb):
        if self._tight_layout:
            plt.tight_layout()
        if not et:
            self._savepath.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(self._savepath)

        plt.close()

        self._rc_context.__exit__(et, ev, tb)

        del self._rc_context
