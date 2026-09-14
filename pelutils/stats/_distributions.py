"""Functions returning SciPy distribution objects reparameterized to Jim Pitman's "Probability"."""

import numpy as np
from scipy import stats


# Continuous distributions
def norm(mu: float, sigma2: float):
    """Return a normal distribution with mean ``mu`` and variance ``sigma2``."""
    assert sigma2 > 0
    return stats.norm(loc=mu, scale=np.sqrt(sigma2))


def lognorm(mu: float, sigma2: float):
    """Return a log-normal distribution where ``log(X)`` has mean ``mu`` and variance ``sigma2``."""
    assert sigma2 > 0
    return stats.lognorm(s=np.sqrt(sigma2), scale=np.exp(mu))


def expon(lambda_: float):
    """Return an exponential distribution with rate ``lambda_`` and mean ``1 / lambda_``."""
    assert lambda_ > 0
    return stats.expon(scale=1 / lambda_)


def gamma(r: float, lambda_: float):
    """Return a gamma distribution with shape ``r`` and rate ``lambda_``."""
    assert r > 0 and lambda_ > 0
    return stats.gamma(a=r, loc=0, scale=1 / lambda_)


def chi2(n: int | float):
    """Return a chi-squared distribution with the given number of degrees of freedom.

    Although degrees of freedom are commonly given as an integer, the distribution
    is here represented as a special case of the gamma distribution, making it defined
    for any positive real ``n``.
    """
    assert n > 0
    return gamma(n / 2, 1 / 2)


def rayleigh():
    """Return a Rayleigh distribution."""
    return stats.rayleigh()


def beta(r: float, s: float):
    """Return a beta distribution."""
    assert r > 0 and s > 0
    return stats.beta(a=r, b=s)


# Discrete distributions
def bernoulli(p: float):
    """Return a Bernoulli distribution with success probability ``p``."""
    assert 0 <= p <= 1
    return stats.bernoulli(p)


def binomial(n: int, p: float):
    """Return a binomial distribution for ``n`` trials with success probability ``p``."""
    assert n >= 0 and 0 <= p <= 1
    return stats.binom(n=n, p=p)


def poisson(mu: float):
    """Return a Poisson distribution with mean and rate ``mu``."""
    assert mu >= 0
    return stats.poisson(mu=mu)


def hypergeom(n: int, N: int, G: int):  # noqa: N803
    """Return a hypergeometric distribution.

    Parameters
    ----------
    n:
        Number of items drawn from the population.
    N:
        Population size.
    G:
        Number of successes in the population.
    """
    assert N > n > 0 and N >= G > 0 and N > 1
    return stats.hypergeom(M=N, n=G, N=n)


def geom0(p: float):
    """Return a geometric distribution of failures before the first success, with success probability ``p``."""
    assert 0 < p <= 1
    return stats.geom(loc=-1, p=p)


def geom1(p: float):
    """Return a geometric distribution of the trial of the first success, with success probability ``p``."""
    assert 0 < p <= 1
    return stats.geom(p=p)


def nbinom(r: int, p: float):
    """Return a negative binomial distribution of failures before ``r`` successes, with success probability ``p``."""
    assert r > 0 and 0 <= p <= 1
    return stats.nbinom(n=r, p=p)
