"""
This module contains utility methods for the .jsonl file format
.jsonl are files where each line is a json string
"""
import json
from typing import Generator, Iterable, TextIO


def load_jsonl(f: TextIO) -> Generator:
    """ Returns a generator of parsed lines in a .jsonl file. Empty lines are ignored """
    for line in f.readlines():
        stripped = line.strip()
        if stripped:
            yield json.loads(stripped)


def write_jsonl(objects: Iterable, f: TextIO, single_block=True):
    """
    Saves an iterable to a .jsonl file
    If single_block is True, objects will be joined to a single block before being written
    It can be usefull to set this to False if there is a large amount of lazily generated data
    """
    if single_block:
        f.write("\n".join(json.dumps(obj) for obj in objects))
    else:
        for obj in objects:
            f.write(json.dumps(obj) + "\n")
