from __future__ import annotations

from typing import Any

from pelutils.datastorage2._pretty_json import _pretty_json  # pyright: ignore[reportPrivateUsage]


def pretty_json(
    obj: dict[str, Any] | list[Any],  # pyright: ignore[reportExplicitAny]
    *,
    max_line_length: int = 140,
    indent: int = 2,
) -> str:
    """Format a dict or list as a human-friendly JSON string. It is very similar to the built-in json.dumps.

    * The root container is always expanded (one element per line).
    * Nested containers stay on one line when they fit within
      *max_line_length*; otherwise they are expanded recursively.
    * Primitive-only lists are bin-packed: items fill each line up to
      *max_line_length* before wrapping to the next.

    Parameters
    ----------
    obj:
        A dict or list (may contain arbitrary Python objects).
    max_line_length:
        Soft limit for line width.
    indent:
        Number of spaces per indentation level.

    Returns
    -------
    str
        A pretty-formatted, valid JSON string.
    """
    return _pretty_json(
        obj,
        max_line_length=max_line_length,
        indent=indent,
        safe=False,
    )
