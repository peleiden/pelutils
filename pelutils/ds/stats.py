from __future__ import annotations

from typing import Any

from pelutils.ds.distributions import norm

__all__ = ("z_score",)


def z_score(alpha: float = 0.05, two_sided: bool = True, distribution: Any | None = None) -> float:  # pyright: ignore[reportExplicitAny]
    """Get z score for a given significance level. The distribution defaults to N(0, 1) but can be any continuous scipy distribution."""
    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be between 0 and 1, not {alpha}")
    if distribution is None:
        distribution = norm(0, 1)
    if two_sided:
        return distribution.ppf(1 - alpha / 2).item()
    else:
        return distribution.ppf(1 - alpha).item()
