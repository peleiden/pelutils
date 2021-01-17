from __future__ import annotations
from typing import Any

from . import _import_error
try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolour
except ModuleNotFoundError as e:
    raise _import_error from e

# All rc params are available here
# https://matplotlib.org/3.2.1/tutorials/introductory/customizing.html#customizing-with-matplotlibrc-files
rc_params       = { "font.size": 24, "legend.fontsize": 22, "legend.framealpha": 0.5 }  # matplotlib settings
rc_params_small = { **rc_params, "font.size": 20, "legend.fontsize": 18 }  # Same but with smaller font

def update_rc_params(rc_params: dict[str, Any]):
    plt.rcParams.update(rc_params)

# Colours
base_colours: list[str] = list(mcolour.BASE_COLORS)  # 8 colours
tab_colours:  list[str] = list(mcolour.TABLEAU_COLORS)  # 10 colours
colours:      list[str] = tab_colours[:-2] + base_colours[:-1]  # 15 unique matplotlib colours

# Common figure sizes
figsize_std  = (15, 10)
figsize_wide = (22, 10)
