from __future__ import annotations

import time
from pathlib import Path
from types import TracebackType
from typing import Any, Callable

import matplotlib.colors as mcolour
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from scipy import stats

from pelutils.types import FloatArray, IntArray

__all__ = (
    "Figure",
    "base_colours",
    "colours",
    "get_dateticks",
    "histogram",
    "linear_binning",
    "log_binning",
    "normal_binning",
    "tab_colours",
)

# 8 colours
base_colours: tuple[str, ...] = tuple(mcolour.BASE_COLORS)
# 10 colours
tab_colours: tuple[str, ...] = tuple(mcolour.TABLEAU_COLORS)
# 15 unique matplotlib colours
colours: tuple[str, ...] = tab_colours[:-2] + base_colours[:-1]


# Utility functions for histograms
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
    """Create bins for plotting a line histogram. Simplest usage is plt.plot(*histogram(data))."""
    found_bins = np.array(binning_fn(data, bins + 1))
    y, edges = np.histogram(data, bins=found_bins, density=density)
    x = (edges[1:] + edges[:-1]) / 2
    if ignore_zeros:
        keep = y > 0
        x, y = x[keep], y[keep]
    return x, y


def get_dateticks(x: npt.ArrayLike, num: int = 6, date_format: str = "%b %d") -> tuple[FloatArray, list[str]]:
    """Produce date labels for the x axis given an array of epoch times in seconds.

    Example
    -------
    ```py
    # x is an array of epoch times in seconds
    plt.plot(x, y)
    plt.xticks(*get_dateticks(x))
    ```
    """
    if not isinstance(num, int) or num < 2:  # pyright: ignore[reportUnnecessaryIsInstance]
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

    def __init__(  # noqa: PLR0913
        self,
        savepath: str | Path,
        *,
        tight_layout: bool = True,
        style: str | None = None,
        # Arguments below here go into mpl.rcParams
        figsize: tuple[float, float] = (15, 10),
        dpi: float = 150,
        fontsize: float = 26,
        title_fontsize: float = 0.5,  # Relative to fontsize
        ticksize: float = 0.85,  # Fraction of fontsize
        labelsize: float = 1,  # Fraction of fontsize
        legend_fontsize: float = 0.85,  # Fraction of fontsize
        legend_framealpha: float = 0.8,
        legend_edgecolor: tuple[float, float, float, float] = (0, 0, 0, 1),
        other_rc_params: dict[str, Any] | None = None,  # pyright: ignore[reportExplicitAny]
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
        """Create a figure."""
        if self._style:
            plt.style.use(self._style)

        self._rc_context = plt.rc_context(self._rc_params)  # pyright: ignore[reportUninitializedInstanceVariable]
        self._rc_context.__enter__()

    def __exit__(self, et: type[BaseException] | None, ev: BaseException | None, tb: TracebackType | None):
        """Close and save figure, and reset _rc_context."""
        if self._tight_layout:
            plt.tight_layout()
        if not et:
            self._savepath.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(self._savepath)

        plt.close()

        self._rc_context.__exit__(et, ev, tb)

        del self._rc_context
