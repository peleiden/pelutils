"""Utility methods for the .jsonl file format. .jsonl are files in which each line is a valid json string."""

import json
from collections.abc import Iterable, Iterator
from typing import Any, TextIO


def jsonl_load(f: TextIO) -> Iterator[str]:
    """Return a generator of parsed lines in a .jsonl file. Empty lines are ignored."""
    for line in f:
        stripped = line.strip()
        if stripped:
            yield json.loads(stripped)


def jsonl_loads(string: str) -> Iterator[str]:
    """Return a generator of parsed lines. Empty lines are ignored."""
    for line in string.splitlines():
        stripped = line.strip()
        if stripped:
            yield json.loads(stripped)


def jsonl_dump(objects: Iterable[Any], f: TextIO, single_block: bool = True):  # pyright: ignore[reportExplicitAny]
    """Save an iterable to a .jsonl file.

    If single_block is True, objects will be joined to a single block before being written.
    It can be usefull to set this to False if there is a large amount of lazily generated data.
    """
    if single_block:
        f.write("\n".join(json.dumps(obj) for obj in objects) + "\n")
    else:
        f.writelines(json.dumps(obj) + "\n" for obj in objects)


def jsonl_dumps(objects: Iterable[Any]) -> str:  # pyright: ignore[reportExplicitAny]
    """Return a string representation of an iterable in a string."""
    return "\n".join(json.dumps(obj) for obj in objects)
