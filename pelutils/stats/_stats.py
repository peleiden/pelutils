from typing import Any

from ._distributions import norm


def z_score(alpha: float = 0.05, two_sided: bool = True, distribution: Any | None = None) -> float:  # pyright: ignore[reportExplicitAny]
    """Return an upper critical value for a given significance level.

    Parameters
    ----------
    alpha : float, optional
        Significance level in ``[0, 1]``.
    two_sided : bool, optional
        If ``True``, use an upper-tail probability of ``alpha / 2``; otherwise use
        ``alpha``. For symmetric distributions this gives the usual two-sided
        cutoff for a distribution symmetric about zero, with the lower cutoff equal
        to the negative of the returned value.
        For asymmetric distributions, the returned value is only the upper cutoff.
    distribution : Any | None, optional
        A frozen SciPy distribution to draw the quantile from. Defaults to ``N(0, 1)``,
        in which case the two-sided default returns the familiar ``~1.96``.
    """
    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be between 0 and 1, not {alpha}")
    if distribution is None:
        distribution = norm(0, 1)
    if two_sided:
        return distribution.ppf(1 - alpha / 2).item()
    else:
        return distribution.ppf(1 - alpha).item()
