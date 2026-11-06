import numpy as np
import pytest
from scipy.stats import norm
from scipy.stats import t as student_t

from pelutils.stats import z_score


def test_z_score():
    with pytest.raises(ValueError):
        z_score(alpha=-0.01)
    with pytest.raises(ValueError):
        z_score(alpha=1.01)
    t = z_score()
    assert np.isclose(norm().cdf(t), 0.975)
    assert np.isclose(norm().cdf(-t), 0.025)

    t = z_score(two_sided=False)
    assert np.isclose(norm().cdf(t), 0.95)
    assert np.isclose(norm().cdf(-t), 0.05)


def test_z_score_distribution():
    dist = student_t(df=5)
    assert np.isclose(z_score(distribution=dist), dist.ppf(0.975))
    assert np.isclose(z_score(two_sided=False, distribution=dist), dist.ppf(0.95))
    # The scale of the distribution must be respected
    assert np.isclose(z_score(distribution=norm(scale=2)), 2 * z_score())
