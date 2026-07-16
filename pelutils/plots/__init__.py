"""Ergonomic ``matplotlib`` plotting with sensible defaults out of the box.

``matplotlib``'s defaults are built for small inline figures: fonts are tiny on a
saved image, every plot needs its own ``savefig``/``close`` boilerplate, and tweaking
``rcParams`` leaks those settings into every later figure in the process.
:class:`Figure` is a context manager that fixes all of this — you get readable font and
figure sizes by default, the figure is saved (creating missing directories) and closed
for you on exit, and the ``rcParams`` changes are scoped to the ``with`` block so they
never bleed into the next plot. The module also bundles the plotting odds and ends that
are fiddly to get right by hand: line :func:`histogram` binning, a set of distinct
:data:`colours`, and human-readable date ticks via :func:`get_dateticks`.

Quick start
-----------

.. code-block:: python

    import matplotlib.pyplot as plt
    from pelutils.plots import Figure, histogram, normal_binning

    with Figure("plot.png", figsize=(20, 10), fontsize=20):
        plt.scatter(x, y, label="Data")
        plt.grid()
        plt.title("Very nice plot")
    # Saved to plot.png and closed here; rcParams restored

    # histogram returns x and y coordinates ready for unpacking into plt.plot
    plt.plot(*histogram(data, binning_fn=normal_binning))

Three binning functions are provided for :func:`histogram` — :func:`linear_binning`,
:func:`log_binning`, and :func:`normal_binning` (more resolution near the centre of
roughly-normal data) — and any custom ``(x, bins) -> edges`` function works too. See
:class:`Figure` for the full list of styling options.
"""

from ._figure import Figure
from ._histogram import histogram, linear_binning, log_binning, normal_binning
from ._utils import base_colours, colours, get_dateticks, tab_colours

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
