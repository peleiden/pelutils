""" This file contains functions that returns scipy.stats distribution
objects reparameterized to Jim Pitman's "Probability". """
import numpy as np
from scipy import stats


# Continuous distributions
def norm(mu: float, sigma2: float):
    assert sigma2 > 0
    return stats.norm(loc=mu, scale=np.sqrt(sigma2))

def lognorm(mu: float, sigma2: float):
    assert sigma2 > 0
    return stats.lognorm(s=np.sqrt(sigma2), scale=np.exp(mu))

def expon(lambda_: float):
    assert lambda_ > 0
    return stats.expon(scale=1/lambda_)

def gamma(r: float, lambda_: float):
    assert r > 0 and lambda_ > 0
    return stats.gamma(a=r, loc=0, scale=1/lambda_)

def chi2(n: int):
    assert n > 0
    return gamma(n/2, 1/2)

def rayleigh():
    return stats.rayleigh()

def beta(r: float, s: float):
    assert r > 0 and s > 0
    return stats.beta(a=r, b=s)

# Discrete distributions
def bernoulli(p: float):
    assert 0 <= p <= 1
    return stats.bernoulli(p)

def binomial(n: int, p: float):
    assert n >= 0 and 0 <= p <= 1
    return stats.binom(n=n, p=p)

def poisson(mu: float):
    assert mu >= 0
    return stats.poisson(mu=mu)

def hypergeom(n: int, N: int, G: int):
    assert N > n and N >= G and N > 1 and n > 0 and G > 0
    return stats.hypergeom(M=N, n=G, N=n)

def geom0(p: float):
    """ The geometric distribution defined on {0, 1, ...} """
    assert 0 < p <= 1
    return stats.geom(loc=-1, p=p)

def geom1(p: float):
    """ The geometric distribution defined on {1, 2, ...} """
    assert 0 < p <= 1
    return stats.geom(p=p)

def nbinom(r: int, p: float):
    assert r > 0 and 0 <= p <= 1
    return stats.nbinom(n=r, p=p)
