import time

import matplotlib.colors as mcolour
import numpy as np
import numpy.typing as npt

from pelutils.types import FloatArray

# 8 colours
base_colours: tuple[str, ...] = tuple(mcolour.BASE_COLORS)
# 10 colours
tab_colours: tuple[str, ...] = tuple(mcolour.TABLEAU_COLORS)
# 15 unique matplotlib colours
colours: tuple[str, ...] = tab_colours[:-2] + base_colours[:-1]


def get_dateticks(x: npt.ArrayLike, num: int = 6, date_format: str = "%b %d") -> tuple[FloatArray, list[str]]:
    """Produce date labels for the x axis given an array of epoch times in seconds.

    Example
    -------

    .. code-block:: python

        # x is an array of epoch times in seconds
        plt.plot(x, y)
        plt.xticks(*get_dateticks(x))
    """
    if not isinstance(num, int) or num < 2:  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError(f"num must int of value 2 or greater, not {num}")
    x = np.array(x)
    xticks = np.linspace(x.min(), x.max(), num)
    xticklabels = [time.strftime(date_format, time.localtime(et)) for et in xticks]
    return xticks, xticklabels
