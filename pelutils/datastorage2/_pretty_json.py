"""Compact-but-readable JSON formatter with pickle fallback for non-serialisable values."""
# A copious amount of Any is used in this file on purpose, so reportExplicitAny is ignored for the whole file
# pyright: reportExplicitAny=false

from __future__ import annotations

import base64
import json
import pickle
from typing import Any

# Sentinel prefix so consumers can detect pickled blobs.
_PICKLE_PREFIX = "__pickled_b64__"


def _get_padding(indent_size: int, depth: int) -> str:
    """Get left-hand whitespace for a JSON element."""
    return " " * (indent_size * depth)


def _inline(value: Any) -> str:
    """Compact one-line JSON representation of an already-safe value."""
    return json.dumps(value, separators=(", ", ": "), ensure_ascii=False)


def _is_primitive(value: Any) -> bool:
    """Check if a value is a Python primitive."""
    return value is None or isinstance(value, (bool, int, float, str))


def _all_primitives(items: list[Any]) -> bool:
    """Check if all elements in the given list is a Python primitive."""
    return all(_is_primitive(item) for item in items)


def _get_qualified_type_name(obj: object) -> str:
    """Get the fully qualified type name of an object (e.g. 'numpy.ndarray')."""
    cls = type(obj)
    module = cls.__module__
    qualname = cls.__qualname__
    if module and module != "builtins":
        return f"{module}.{qualname}"
    return qualname


def _pickle_encode(value: object) -> str:
    """Pickle *value*, base64-encode the bytes, and return a prefixed string."""
    raw = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"{_PICKLE_PREFIX}:{_get_qualified_type_name(value)}:{encoded}"


def _decode_unpickle(encoded: str) -> Any:
    """Decode a single ``__pickled_b64__:…`` string back to its Python object."""
    try:
        prefix, _qualified_type, b64 = encoded.split(":")
    except ValueError as e:
        raise ValueError(f"Not a pickled value: {encoded!r}") from e
    assert prefix == _PICKLE_PREFIX, f'Bad pickle prefix "{prefix}"'
    return pickle.loads(base64.b64decode(b64))


def _make_json_safe(value: Any) -> Any:
    """Recursively convert *value* into a JSON-safe structure.

    Dicts, lists, tuples, and JSON-native scalars pass through.
    Anything else is replaced with a ``__pickled_b64__:…`` string.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, dict):
        return {str(k): _make_json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]

    # Non-serialisable → pickle + b64
    return _pickle_encode(value)


def _make_json_unsafe(value: Any) -> Any:
    """Recursively convert *value* from a JSON-safe structure.

    b64encoded strings are decoded and unpickled. Everything else is passed through.
    """
    if isinstance(value, str) and value.startswith(f"{_PICKLE_PREFIX}:"):
        return _decode_unpickle(value)

    if isinstance(value, dict):
        return {str(k): _make_json_unsafe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_make_json_unsafe(item) for item in value]

    return value


def _pack_primitive_list(
    items: list[Any],
    depth: int,
    max_line_length: int,
    indent_size: int,
) -> str:
    """Format a list of JSON primitives, bin-packing items onto lines.

    Each line is filled left-to-right up to *max_line_length* before
    starting a new one. At least one item is always placed per line
    (graceful overflow for irreducibly long scalars).
    """
    child_pad = _get_padding(indent_size, depth + 1)
    close_pad = _get_padding(indent_size, depth)

    serialised = [json.dumps(item, ensure_ascii=False) for item in items]

    lines: list[list[str]] = []
    current_items: list[str] = []
    current_len = len(child_pad)

    for s in serialised:
        if not current_items:
            # First item on a line — always accept it (even if it overflows).
            current_items.append(s)
            current_len = len(child_pad) + len(s)
        else:
            tentative = current_len + len(", ") + len(s)
            if tentative <= max_line_length:
                current_items.append(s)
                current_len = tentative
            else:
                lines.append(current_items)
                current_items = [s]
                current_len = len(child_pad) + len(s)

    if current_items:
        lines.append(current_items)

    formatted = [child_pad + ", ".join(group) for group in lines]
    return "[\n" + ",\n".join(formatted) + f"\n{close_pad}]"


def _format_value(  # noqa: PLR0911, PLR0913
    value: Any,
    depth: int,
    max_line_length: int,
    indent_size: int,
    *,
    force_expand: bool = False,
    line_prefix_len: int | None = None,
) -> str:  # pyright: ignore[reportReturnType]
    """Recursively format a *JSON-safe* value into a pretty string."""
    if _is_primitive(value):
        return json.dumps(value, ensure_ascii=False)

    prefix_len = line_prefix_len if line_prefix_len is not None else depth * indent_size

    # ── Try compact single-line form ──
    if not force_expand:
        inline = _inline(value)
        if prefix_len + len(inline) <= max_line_length:
            return inline

    # ── Expand dict ──
    child_pad = _get_padding(indent_size, depth + 1)
    close_pad = _get_padding(indent_size, depth)

    if isinstance(value, dict):
        if not value:
            return "{}"
        entries: list[str] = []
        for k, v in value.items():
            key_str = json.dumps(k, ensure_ascii=False)
            entry_prefix = f"{child_pad}{key_str}: "
            val_str = _format_value(
                v,
                depth + 1,
                max_line_length,
                indent_size,
                line_prefix_len=len(entry_prefix),
            )
            entries.append(f"{entry_prefix}{val_str}")
        return "{\n" + ",\n".join(entries) + f"\n{close_pad}}}"

    # ── Expand list ──
    if isinstance(value, list):
        if not value:
            return "[]"
        # Primitive-only lists get bin-packed across lines.
        if _all_primitives(value):
            return _pack_primitive_list(value, depth, max_line_length, indent_size)
        # Mixed / nested lists: one element per line.
        items: list[str] = []
        for item in value:
            item_str = _format_value(
                item,
                depth + 1,
                max_line_length,
                indent_size,
                line_prefix_len=len(child_pad),
            )
            items.append(f"{child_pad}{item_str}")
        return "[\n" + ",\n".join(items) + f"\n{close_pad}]"

    # Nothing is returned here
    # The code should be unreachable


def _pretty_json(  # pyright: ignore[reportUnusedFunction]
    obj: dict[str, Any] | list[Any],
    *,
    max_line_length: int,
    indent: int,
    safe: bool,
) -> str:
    """Convert the object into a pretty, human-readable JSON file.

    See `pelutils/pretty_json.py` for argument details.

    It is possible to set safe=True. In that case, any value that is not natively JSON-serialisable is pickled,
    base64-encoded, and stored as a "__pickled_b64__:type_name:b64" string.
    """
    assert max_line_length > 1
    assert indent >= 0
    if safe:
        obj = _make_json_safe(obj)
    return _format_value(
        obj,
        depth=0,
        max_line_length=max_line_length,
        indent_size=indent,
        force_expand=True,
    )
