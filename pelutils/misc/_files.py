"""File and file system related functionality."""

import os
from collections.abc import Generator
from io import DEFAULT_BUFFER_SIZE
from typing import TextIO

from pelutils.misc._platform import OS, UnsupportedOS


def _read_file_chunk(file: TextIO, chunksize: int) -> str:
    """Read a chunk starting from `chunksize` before file pointer and up to current file pointer.

    If `chunksize` is larger than the current file pointer, the file is read from the beginning.
    Returns the read content in reverse order and moves the file pointer to where the content starts.
    Reverse order is used, as it will be mostly faster to search for newlines,
    especially if there are many lines in a given chunk.
    """
    mov = file.tell() - max(file.tell() - chunksize, 0)
    file.seek(file.tell() - mov)
    reversed_content = file.read(mov)[::-1]
    file.seek(file.tell() - mov)
    return reversed_content


def reverse_line_iterator(file: TextIO, chunksize: int = DEFAULT_BUFFER_SIZE, linesep: str = "\n") -> Generator[str, None, None]:
    """Similar to file.readlines(), but lazily returns lines in reverse order.

    Will move file pointer (file.tell()) throughout execution, so be careful.
    When done, file pointer will be 0. This function is especially useful for large files,
    as it will never take up more memory that size of largest line + chunksize.
    Raises an OSError on Windows, as this function currently is not supported on Windows due
    to fuckery in how line seperators are read.
    """
    if OS.is_windows:
        raise UnsupportedOS("reverse_line_iterator is not supported on Windows")
    if len(linesep) != 1:
        raise ValueError("reverse_line_iterator only supports line seperators of length 1")

    # Go to end of file and read first chunk
    file.seek(0, os.SEEK_END)
    reversed_content = _read_file_chunk(file, chunksize)
    reversed_contents = list()
    while True:
        try:
            # Try finding the next newline
            idx = reversed_content.index(linesep, 1)
            # Yield everything up to the newline (as the content is reversed)
            yield_, reversed_content = reversed_content[:idx], reversed_content[idx:]
            reversed_contents.append(yield_)
            yield "".join(reversed_contents)[::-1]
            reversed_contents = list()
        except ValueError:
            # No newline was found, so read a new chunk
            reversed_contents.append(reversed_content)
            reversed_content = _read_file_chunk(file, chunksize)
            if not reversed_content:
                break

    yield "".join(reversed_contents)[::-1]
