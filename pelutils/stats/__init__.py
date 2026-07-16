"""Statistical helpers and scipy distributions parametrised the way textbooks are.

``scipy.stats`` parametrises every distribution through generic ``loc``/``scale``
arguments, which rarely match how a distribution is actually defined: an exponential's
``scale`` is ``1 / lambda``, a normal takes a standard deviation rather than a variance,
and a gamma's ``a``/``scale`` bear no obvious relation to its shape and rate. This module
wraps the scipy distributions so you pass their *natural* parameters instead — following
the conventions in Jim Pitman's *Probability* — and returns an ordinary frozen scipy
distribution, so ``.pdf``, ``.cdf``, ``.rvs`` and friends all work as usual. It also
provides :func:`z_score` for turning a significance level into a critical value.

Quick start
-----------

.. code-block:: python

    from pelutils.stats import expon, norm, z_score

    dist = norm(mu=0, sigma2=4)   # mean and *variance*, not standard deviation
    dist.cdf(1.5)                 # a plain frozen scipy distribution

    # 95 % confidence-interval half-width for a standard normal (defaults give ~1.96)
    half_width = std * z_score()

    # One-sided z value for an Exponential(lambda=2) at the 1 % significance level
    zval = z_score(alpha=0.01, two_sided=False, distribution=expon(lambda_=2))

Continuous distributions: :func:`norm`, :func:`lognorm`, :func:`expon`, :func:`gamma`,
:func:`chi2`, :func:`rayleigh`, :func:`beta`. Discrete distributions: :func:`bernoulli`,
:func:`binomial`, :func:`poisson`, :func:`hypergeom`, :func:`geom0`, :func:`geom1`,
:func:`nbinom`.
"""

from ._distributions import bernoulli, beta, binomial, chi2, expon, gamma, geom0, geom1, hypergeom, lognorm, nbinom, norm, poisson, rayleigh
from ._stats import z_score

__all__ = (
    "bernoulli",
    "beta",
    "binomial",
    "chi2",
    "expon",
    "gamma",
    "geom0",
    "geom1",
    "hypergeom",
    "lognorm",
    "nbinom",
    "norm",
    "poisson",
    "rayleigh",
    "z_score",
)
