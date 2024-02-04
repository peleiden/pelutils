import os
import time
from datetime import datetime, timedelta
from itertools import product
from math import ceil

import matplotlib as mpl
import numpy as np
import pytest

from pelutils.tests import UnitTestCollection
from pelutils.ds.plots import linear_binning, log_binning, normal_binning, \
    colours, base_colours, tab_colours, \
    moving_avg, exp_moving_avg, double_moving_avg, \
    Figure, get_dateticks, histogram


def test_colours():
    assert len(base_colours) == len(set(base_colours)) ==  8
    assert len(tab_colours)  == len(set(tab_colours))  == 10
    assert len(colours)      == len(set(colours))      == 15

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

class TestMovingAverage:

    def test_moving_avg(self):
        data = np.random.randn(100)
        num_neighs = np.arange(1, 10)

        # First, test with only y given
        for n in num_neighs:
            x, mov = moving_avg(data, neighbors=n)
            assert len(x) == len(mov) == len(data) - 2 * n
            assert mov.std() < data.std()

        # Then test with both x and y given
        for n in num_neighs:
            x = np.linspace(0, 10, len(data))
            x, mov = moving_avg(x, data, neighbors=n)
            assert len(x) == len(mov) == len(data) - 2 * n
            assert mov.std() < data.std()

        # Test that it converges as expected
        for n in num_neighs:
            data = np.linspace(-10, 10, 1000)
            dist_to_zero = np.linalg.norm(data-np.zeros_like(data))
            prev_dist_to_zero = dist_to_zero
            while len(data) > 2 * n:
                _, data = moving_avg(data, neighbors=n)
                dist_to_zero = np.linalg.norm(data-np.zeros_like(data))
                assert 0 <= dist_to_zero < prev_dist_to_zero
                prev_dist_to_zero = dist_to_zero

    def test_exp_moving_avg(self):
        data = np.random.randn(100)
        # alpha is 1, so data should be unchanged
        x, y = exp_moving_avg(data, alpha=1)
        assert len(x) == len(y) == len(data)
        assert np.all(np.isclose(data, y))

        # alpha is 0, so data should be equal to the first point
        x, y = exp_moving_avg(data, alpha=0)
        assert len(x) == len(y) == len(data)
        assert np.all(np.isclose(data[0], y))

        # Test that reverse works. For alpha = 0, data should be
        # equal to the last point
        x, y = exp_moving_avg(data, alpha=0, reverse=True)
        assert len(x) == len(y) == len(data)
        assert np.all(np.isclose(data[-1], y))

        # For monotically increasing data, the data should lag behind
        # except for the first point, which is the same
        data = np.linspace(-10, 10)
        x, y = exp_moving_avg(data)
        assert np.all(y[1:]<data[1:])
        assert np.isclose(data[0], y[0])

        # Corresponding test for reversed
        data = np.linspace(-10, 10)
        x, y = exp_moving_avg(data, reverse=True)
        assert np.all(y[:-1]>data[:-1])
        assert np.isclose(data[-1], y[-1])

        # Test that it also works when supplying x
        x = np.linspace(-np.pi, np.pi)
        data = np.sin(x) + np.random.randn(len(x))
        x_smooth, y_smooth = exp_moving_avg(x, data)
        assert len(x) == len(data) == len(x_smooth) == len(y_smooth)
        assert (x == x_smooth).all()

    def test_double_moving_avg(self):
        test_samples = np.arange(100, 500, step=65)
        test_inner_neighbors = np.arange(1, 10)
        test_outer_neighbors = np.arange(1, 10)
        data = np.random.randn(200)

        for s, i, o in product(test_samples, test_inner_neighbors, test_outer_neighbors):
            x, y = double_moving_avg(data, inner_neighbors=i, outer_neighbors=o, samples=s)
            assert len(x) == len(y) == s
            assert y.std() < data.std()

        # Test that it also works when supplying x
        x = np.linspace(-np.pi, np.pi)
        data = np.sin(x) + np.random.randn(len(x))
        samples = 300
        x_smooth, y_smooth = double_moving_avg(x, data, samples=300)
        assert len(x_smooth) == len(y_smooth) == samples
        assert y_smooth.std() < data.std()

    def test_list_arg_avg(self):
        # Test that it works when supplying lists instead of numpy arrays
        moving_avg([1, 2, 3])
        moving_avg([1, 2, 3], [1, 2, 3])
        exp_moving_avg([1, 2, 3])
        exp_moving_avg([1, 2, 3], [1, 2, 3])
        double_moving_avg([1, 2, 3])
        double_moving_avg([1, 2, 3], [1, 2, 3])

class TestBinning:

    bins = 25
    uniform_data = np.random.uniform(1, 200, 500)

    def test_linear_binning(self):
        binning = linear_binning(self.uniform_data, self.bins)
        diffs = np.diff(binning)
        for a, b in zip(diffs[:-1], diffs[1:]):
            assert np.isclose(a, b)

    def test_log_binning(self):
        binning = log_binning(self.uniform_data, self.bins)
        ratios = binning[1:] / binning[:-1]
        diffs = np.diff(ratios)
        for a, b in zip(diffs[:-1], diffs[1:]):
            assert np.isclose(a, b)

    def test_normal_binning(self):
        binning = normal_binning(self.uniform_data, self.bins)
        for i in range(ceil(self.bins / 2)):
            assert np.isclose(binning[i+1]-binning[i], binning[self.bins-i-1]-binning[self.bins-i-2])
        assert (np.diff(binning, n=3) > 0).all()

class TestFigure(UnitTestCollection):

    savepath = os.path.join(UnitTestCollection.test_dir, "test.png")

    def test_save(self):
        with Figure(self.savepath):
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
                0 / 0
            assert not os.path.exists(self.savepath)

    def test_restore_rc_params(self):
        default_fontsize = mpl.rcParams["font.size"]
        default_ytick_right = mpl.rcParams["ytick.right"]
        new_fontsize = default_fontsize + 1
        new_ytick_right = not default_ytick_right

        with Figure(
            self.savepath,
            fontsize=new_fontsize,
            other_rc_params={ "ytick.right": new_ytick_right },
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
