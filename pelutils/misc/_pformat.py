"""Pretty-formatting of objects, including Pydantic models."""

from rich.pretty import pretty_repr


def pformat(obj: object, width: int = 80) -> str:
    """Pretty-format an object as a string using Rich's pretty-printing style.

    Unlike :func:`pprint.pformat`, Pydantic models are split over multiple lines
    when they do not fit within ``width``. Pydantic models are formatted from their
    fields, even if they override ``__repr__``. The layout otherwise differs from
    :func:`pprint.pformat`, and dict keys are not sorted.

    Parameters
    ----------
    obj : object
        Object to format.
    width : int, optional
        Maximum line width. Lines may still exceed this if a value cannot be split.

    Returns
    -------
    str
        The formatted representation without a trailing newline.
    """
    return pretty_repr(obj, max_width=width)
