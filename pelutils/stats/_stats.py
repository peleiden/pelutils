from typing import Any

from ._distributions import norm


def z_score(alpha: float = 0.05, two_sided: bool = True, distribution: Any | None = None) -> float:  # pyright: ignore[reportExplicitAny]
    """Return the critical value (z score) for a given significance level.

    Parameters
    ----------
    alpha : float, optional
        Significance level in ``[0, 1]``.
    two_sided : bool, optional
        If ``True``, split ``alpha`` across both tails; otherwise use a single tail.
    distribution : Any | None, optional
        A frozen scipy distribution to draw the quantile from. Defaults to ``N(0, 1)``,
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
