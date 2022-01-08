import numpy as np
import pytest

from pelutils.ds.stats import corr_ci


@pytest.mark.filterwarnings("ignore:divide by zero")
@pytest.mark.filterwarnings("ignore:invalid value")
def test_corr_ci():
    # Test some basic cases
    cci = corr_ci([0, 3], [0, 1])
    assert cci[0] == 1 and cci[3] == 1
    assert np.isnan(cci[1]) and np.isnan(cci[2])

    cci = corr_ci([0, -3], [0, 1])
    assert cci[0] == -1 and cci[3] == 1
    assert np.isnan(cci[1]) and np.isnan(cci[2])

    # Test that different iterable types are properly handled
    cci = corr_ci((x for x in range(2)), (x for x in range(2)))
    assert cci[0] == 1 and cci[3] == 1
    assert np.isnan(cci[1]) and np.isnan(cci[2])

    xiter = iter([0, 1])
    yiter = iter([0, -1/2])
    cci = corr_ci(xiter, yiter)
    assert cci[0] == -1 and cci[3] == 1
    assert np.isnan(cci[1]) and np.isnan(cci[2])

    assert isinstance(corr_ci([0, 3], [0, 1], return_string=True), str)
