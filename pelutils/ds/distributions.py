from . import _import_error

try:
    from scipy import stats
except ModuleNotFoundError as e:
    raise _import_error from e
import numpy as np


# Continuous distributions using the same parameters as in Jim Pitman's "Probability"
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
    assert r > 0, s > 0
    return stats.beta(a=r, b=s)

# Discrete distributions using the same parameters as in Jim Pitman's "Probability"
def bernoulli(p: float):
    assert 0 <= p <= 1
    return stats.bernoulli(p)

def binomial(n: int, p: float):
    assert 0 <= p <= 1
    return stats.binom(n=n, p=p)

def poisson(mu: float):
    return stats.poisson(mu=mu)

def hypergeom(n: int, N: int, G: int):
    assert N >= n and N >= G
    return stats.hypergeom(M=N, n=G, N=n)

def geom(p: float):
    assert 0 <= p <= 1
    return stats.geom(p=p)

def nbinom(r: int, p: float):
    assert r >= 0 and 0 <= p <= 1
    return stats.nbinom(n=r, p=p)
