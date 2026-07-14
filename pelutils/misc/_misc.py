"""The truly miscellaenous functionality."""

from collections.abc import Iterable
from typing import TypeVar

_T = TypeVar("_T")
_V = TypeVar("_V")


def except_keys(d: dict[_T, _V], except_keys: Iterable[_T]) -> dict[_T, _V]:
    """Return a shallow copy of the given dictionary, but with given keys removed."""
    except_keys = set(except_keys)
    return {kw: v for kw, v in d.items() if kw not in except_keys}
