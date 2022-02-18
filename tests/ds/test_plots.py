from math import ceil

import numpy as np

from pelutils.tests import UnitTestCollection
from pelutils.ds.plots import linear_binning, log_binning, normal_binning, colours


def test_colours():
    expected_colours = 15
    assert len(colours) == expected_colours
    # Teste uniqueness
    assert len(set(colours)) == expected_colours

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
        assert (np.diff(np.diff(np.diff(binning))) > 0).all()
