import os
from datetime import datetime, timedelta
from itertools import pairwise
from math import ceil
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pytest

from pelutils.ds.plots import (
    Figure,
    base_colours,
    colours,
    get_dateticks,
    histogram,
    linear_binning,
    log_binning,
    normal_binning,
    tab_colours,
)
from pelutils.tests import UnitTestCollection


def test_colours():
    assert len(base_colours) == len(set(base_colours)) == 8
    assert len(tab_colours) == len(set(tab_colours)) == 10
    assert len(colours) == len(set(colours)) == 15


def test_get_dateticks():
    start_time = datetime.now()
    end_time = start_time + timedelta(days=10)

    num_datapoints = 50
    x = np.linspace(start_time.timestamp(), end_time.timestamp(), num_datapoints)

    for num_ticks in range(10):
        if num_ticks < 2:
            with pytest.raises(ValueError):
                get_dateticks(x, num_ticks)
        else:
            with pytest.raises(ValueError):
                get_dateticks(x, float(num_ticks))
            ticks, labels = get_dateticks(x, num_ticks)
            assert num_ticks == len(ticks) == len(labels)
            assert np.isclose(x[0], ticks[0])
            assert np.isclose(x[-1], ticks[-1])
            assert labels[0] == start_time.strftime("%b %d")
            assert labels[-1] == end_time.strftime("%b %d")


def test_histogram():
    obs = [1, 2, 2, 1, 2]
    x, y = histogram(obs)
    assert isinstance(x, np.ndarray)
    assert isinstance(y, np.ndarray)
    assert (y >= 0).all()

    x, y = histogram(obs, ignore_zeros=True)
    assert (y > 0).all()


class TestBinning:
    bins = 25
    uniform_data = np.random.uniform(1, 200, 500)  # noqa: NPY002

    def test_linear_binning(self):
        binning = linear_binning(self.uniform_data, self.bins)
        diffs = np.diff(binning)
        for a, b in pairwise(diffs):
            assert np.isclose(a, b)

    def test_log_binning(self):
        binning = log_binning(self.uniform_data, self.bins)
        ratios = binning[1:] / binning[:-1]
        diffs = np.diff(ratios)
        for a, b in pairwise(diffs):
            assert np.isclose(a, b)

    def test_normal_binning(self):
        binning = normal_binning(self.uniform_data, self.bins)
        for i in range(ceil(self.bins / 2)):
            assert np.isclose(binning[i + 1] - binning[i], binning[self.bins - i - 1] - binning[self.bins - i - 2])
        assert (np.diff(binning, n=3) > 0).all()


class TestFigure(UnitTestCollection):
    @property
    def savepath(self) -> str:
        return self.get_test_path("test.png")

    def test_save(self):
        with Figure(Path(self.savepath)):
            pass
        assert os.path.isfile(self.savepath)
        path = os.path.join(UnitTestCollection.test_dir, "many", "long", "subdirectories.png")
        with Figure(path):
            pass
        assert os.path.isfile(path)

    def test_no_save_if_error(self):
        if os.path.exists(self.savepath):
            os.remove(self.savepath)

        with Figure(self.savepath):
            pass
        assert os.path.exists(self.savepath)
        os.remove(self.savepath)

        with pytest.raises(ZeroDivisionError):
            with Figure(self.savepath):
                0 / 0  # noqa: B018
            assert not os.path.exists(self.savepath)

    def test_restore_rc_params(self):
        default_fontsize = mpl.rcParams["font.size"]
        default_ytick_right = mpl.rcParams["ytick.right"]
        new_fontsize = default_fontsize + 1
        new_ytick_right = not default_ytick_right

        with Figure(
            self.savepath,
            fontsize=new_fontsize,
            other_rc_params={"ytick.right": new_ytick_right},
        ):
            assert mpl.rcParams["font.size"] == new_fontsize
            assert mpl.rcParams["ytick.right"] == new_ytick_right
        assert mpl.rcParams["font.size"] == default_fontsize
        assert mpl.rcParams["ytick.right"] == default_ytick_right

    def test_stylesheet(self):
        with pytest.raises(OSError), Figure(self.savepath, style="this-style-does-not exist", tight_layout=True):
            pass
        with Figure(self.savepath, style="classic", tight_layout=True):
            pass
