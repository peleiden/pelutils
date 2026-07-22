from pathlib import Path
from types import TracebackType
from typing import Any

import matplotlib.pyplot as plt


class Figure:
    """Context manager that applies plotting defaults and saves the figure on exit.

    On entering the ``with`` block the given ``rcParams`` are applied within a scoped
    context; on exit the figure is saved to ``savepath`` (creating missing parent
    directories), the figure is closed, and the previous ``rcParams`` are restored. If
    the block raises, the figure is closed without saving.

    Parameters
    ----------
    savepath : str | Path
        Where the figure is written on a clean exit.
    tight_layout : bool, optional
        Call ``plt.tight_layout()`` before saving.
    style : str | None, optional
        Name of a matplotlib style to apply, e.g. ``"seaborn-v0_8"``.
    figsize : tuple[float, float], optional
        Figure size in inches.
    dpi : float, optional
        Resolution of the saved figure.
    fontsize : float, optional
        Base font size. Specific font sizes are given as a fraction of this value.
    title_fontsize, ticksize, labelsize, legend_fontsize : float, optional
        Title, tick-label, axis-label, and legend font sizes, each as a fraction of
        ``fontsize``.
    legend_framealpha : float, optional
        Opacity of the legend background.
    legend_edgecolor : tuple[float, float, float, float], optional
        RGBA colour of the legend border.
    other_rc_params : dict[str, Any] | None, optional
        Extra ``rcParams`` merged in last, overriding any of the above.

    Example
    -------

    .. code-block:: python

        with Figure("figure.png", figsize=(20, 10), fontsize=50):
            plt.plot(x, y)
            plt.title("Very large title")
            plt.grid()

        # The finished figure is saved to "figure.png".
        # All settings are reset here.
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
        title_fontsize: float = 0.5,  # Fraction of fontsize
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

        self._rc_params: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
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
        self._rc_context = None

    def __enter__(self):
        """Create a figure."""
        if self._style:
            plt.style.use(self._style)

        # This can be improved with RcKeyType but that was only introduced in matplotlib 3.11
        # To maintain compatibility with older versions, str is used which makes the type checked complain on newest installs
        self._rc_context = plt.rc_context(self._rc_params)  # pyright: ignore[reportArgumentType]
        self._rc_context.__enter__()

    def __exit__(self, et: type[BaseException] | None, ev: BaseException | None, tb: TracebackType | None):
        """Close and save figure, and reset _rc_context."""
        assert self._rc_context is not None
        if self._tight_layout:
            plt.tight_layout()
        if not et:
            self._savepath.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(self._savepath)

        plt.close()

        self._rc_context.__exit__(et, ev, tb)

        self._rc_context = None
