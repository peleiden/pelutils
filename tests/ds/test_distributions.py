from itertools import product

import numpy as np
import pytest

from pelutils.ds.distributions import\
    norm, lognorm, expon, gamma, chi2, rayleigh, beta, \
    bernoulli, binomial, poisson, hypergeom, geom0, geom1, nbinom


def test_norm():
    mus = np.linspace(-10, 10, 5)
    sigmas = np.linspace(0, 10, 5)[1:]
    for mu, sigma in product(mus, sigmas):
        dist = norm(mu, sigma**2)
        assert np.isclose(dist.mean(), mu)
        assert np.isclose(dist.var(), sigma**2)

def test_lognorm():
    mus = np.linspace(-10, 10, 5)
    sigmas = np.linspace(0, 10, 5)[1:]
    for mu, sigma in product(mus, sigmas):
        dist = lognorm(mu, sigma**2)
        assert np.isclose(dist.mean(), np.exp(mu+sigma**2/2))
        assert np.isclose(dist.var(), (np.exp(sigma**2)-1)*np.exp(2*mu+sigma**2))

def test_expon():
    lambdas = np.linspace(0, 10, 5)[1:]
    for l in lambdas:
        dist = expon(l)
        assert np.isclose(dist.mean(), 1/l)
        assert np.isclose(dist.var(), 1/l**2)

def test_gamma():
    rs = np.linspace(0, 10, 5)[1:]
    lambdas = np.linspace(0, 10)[1:]
    for r, l in product(rs, lambdas):
        dist = gamma(r, l)
        assert np.isclose(dist.mean(), r/l)
        assert np.isclose(dist.var(), r/l**2)

def test_chi2():
    dfs = np.linspace(0, 10, 31)[1:]
    for df in dfs:
        dist = chi2(df)
        assert np.isclose(dist.mean(), df)
        assert np.isclose(dist.var(), 2*df)

def test_rayleigh():
    dist = rayleigh()
    assert np.isclose(dist.mean(), np.sqrt(np.pi/2))
    assert np.isclose(dist.var(), (4-np.pi)/2)

def test_beta():
    rs = np.linspace(0, 10, 5)[1:]
    ss = np.linspace(0, 10, 5)[1:]
    for r, s in product(rs, ss):
        dist = beta(r, s)
        assert np.isclose(dist.mean(), r/(r+s))
        assert np.isclose(dist.var(), r*s/((r+s)**2*(r+s+1)))

def test_bernoulli():
    ps = np.linspace(0, 1, 5)
    for p in ps:
        dist = bernoulli(p)
        assert np.isclose(dist.mean(), p)
        assert np.isclose(dist.var(), p*(1-p))

def test_binomial():
    ns = np.arange(0, 10)
    ps = np.linspace(0, 1, 5)
    for n, p in product(ns, ps):
        dist = binomial(n, p)
        assert np.isclose(dist.mean(), n*p)
        assert np.isclose(dist.var(), n*p*(1-p))

def test_poisson():
    mus = np.linspace(0, 10, 5)
    for mu in mus:
        dist = poisson(mu)
        assert np.isclose(dist.mean(), mu)
        assert np.isclose(dist.var(), mu)

@pytest.mark.filterwarnings("ignore:invalid value", "ignore:divide by zero")
def test_hypergeom():
    ns = np.arange(0, 10)
    Ns = np.arange(0, 10)
    Gs = np.arange(0, 10)
    for n, N, G in product(ns, Ns, Gs):
        if n >= N or G > N or n == 0 or N <= 1 or G == 0:
            with pytest.raises(AssertionError):
                dist = hypergeom(n, N, G)
            continue
        dist = hypergeom(n, N, G)
        assert np.isclose(dist.mean(), n*G/N)
        assert np.isclose(dist.var(), n*G/N*(N-G)/N*(N-n)/(N-1))

@pytest.mark.filterwarnings("ignore:divide by zero")
def test_geom0():
    ps = np.linspace(0, 1, 5)[1:]
    for p in ps:
        dist = geom0(p)
        assert np.isclose(dist.mean(), (1-p)/p)
        assert np.isclose(dist.var(), (1-p)/p**2)

@pytest.mark.filterwarnings("ignore:divide by zero")
def test_geom1():
    ps = np.linspace(0, 1, 5)[1:]
    for p in ps:
        dist = geom1(p)
        assert np.isclose(dist.mean(), 1/p)
        assert np.isclose(dist.var(), (1-p)/p**2)

@pytest.mark.filterwarnings("ignore:divide by zero")
def test_nbinom():
    rs = np.arange(0, 10)[1:]
    ps = np.linspace(0, 1, 5)[1:]
    for r, p in product(rs, ps):
        dist = nbinom(r, p)
        assert np.isclose(dist.mean(), r*(1-p)/p)
        assert np.isclose(dist.var(), r*(1-p)/p**2)
