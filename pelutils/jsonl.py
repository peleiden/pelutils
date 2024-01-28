""" This module contains utility methods for the .jsonl file format.
.jsonl are files where each line is a json string. """
import os
from typing import Generator, Iterable, TextIO

import rapidjson


def load(f: TextIO) -> Generator:
    """ Returns a generator of parsed lines in a .jsonl file. Empty lines are ignored. """
    for line in f:
        stripped = line.strip()
        if stripped:
            yield rapidjson.loads(stripped)

def loads(string: str) -> Generator:
    """ Returns a generator of parsed lines. Empty lines are ignored. """
    for line in string.splitlines():
        stripped = line.strip()
        if stripped:
            yield rapidjson.loads(stripped)

def dump(objects: Iterable, f: TextIO, single_block=True):
    """ Saves an iterable to a .jsonl file.
    If single_block is True, objects will be joined to a single block before being written.
    It can be usefull to set this to False if there is a large amount of lazily generated data. """
    if single_block:
        f.write(os.linesep.join(rapidjson.dumps(obj) for obj in objects) + os.linesep)
    else:
        for obj in objects:
            f.write(rapidjson.dumps(obj) + os.linesep)

def dumps(objects: Iterable) -> str:
    """ Returns a string representation of an iterable in a string. """
    return os.linesep.join(rapidjson.dumps(obj) for obj in objects)
