"""Functions returning scipy.stats distribution objects reparameterized to Jim Pitman's "Probability"."""
import numpy as np
from scipy import stats


# Continuous distributions
def norm(mu: float, sigma2: float):
    """Return a normal distribution from mean and variance."""
    assert sigma2 > 0
    return stats.norm(loc=mu, scale=np.sqrt(sigma2))

def lognorm(mu: float, sigma2: float):
    """Return a log normal distribution from the mean and variance of the corresponding normal distribution."""
    assert sigma2 > 0
    return stats.lognorm(s=np.sqrt(sigma2), scale=np.exp(mu))

def expon(lambda_: float):
    """Return an exponential distribution."""
    assert lambda_ > 0
    return stats.expon(scale=1/lambda_)

def gamma(r: float, lambda_: float):
    """Return a gamma distribution."""
    assert r > 0 and lambda_ > 0
    return stats.gamma(a=r, loc=0, scale=1/lambda_)

def chi2(n: int):
    """Return a chi squared distribution."""
    assert n > 0
    return gamma(n/2, 1/2)

def rayleigh():
    """Return a rayleigh distribution."""
    return stats.rayleigh()

def beta(r: float, s: float):
    """Return a beta distribution."""
    assert r > 0 and s > 0
    return stats.beta(a=r, b=s)

# Discrete distributions
def bernoulli(p: float):
    """Return a Bernoulli distribution."""
    assert 0 <= p <= 1
    return stats.bernoulli(p)

def binomial(n: int, p: float):
    """Return a binomial distribution."""
    assert n >= 0 and 0 <= p <= 1
    return stats.binom(n=n, p=p)

def poisson(mu: float):
    """Return a Poisson distribution."""
    assert mu >= 0
    return stats.poisson(mu=mu)

def hypergeom(n: int, N: int, G: int):
    """Return a hypergeometric distribution."""
    assert N > n and N >= G and N > 1 and n > 0 and G > 0
    return stats.hypergeom(M=N, n=G, N=n)

def geom0(p: float):
    """Return a geometric distribution defined on {0, 1, ...}."""
    assert 0 < p <= 1
    return stats.geom(loc=-1, p=p)

def geom1(p: float):
    """Return a geometric distribution defined on {1, 2, ...}."""
    assert 0 < p <= 1
    return stats.geom(p=p)

def nbinom(r: int, p: float):
    """Return a negative binomial distribution."""
    assert r > 0 and 0 <= p <= 1
    return stats.nbinom(n=r, p=p)
