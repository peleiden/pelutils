from __future__ import annotations
from typing import Any, Iterable
import regex

from rich.console import Console


_stdout_console = Console(highlight=False)
_stderr_console = Console(highlight=False, stderr=True)

class RichString:

    """
    Class used for combining normal strings and rich strings
    This allows for printing and logging without rich syntax causing issues
    """

    def __init__(self, stderr=False):
        self.strings: list[str] = list()  # Normal strings
        self.riches:  list[str] = list()  # Corresponding strings with rich syntax
        self.console = _stderr_console if stderr else _stdout_console

    def add_string(self, s: str, rich: str=None):
        """ Add a new string and optionally a rich string equivalent """
        if rich is None:
            # Escape beginning brackets to prevent accidental formatting when printing
            rich = regex.sub(r"(\[[a-zA-Z\s]+\])", r"\\\1", s)
            rich = regex.sub(r"(\[\/\])", r"\\\1", rich)
        self.strings.append(s)
        self.riches.append(rich)

    def print(self):
        """ Print rich text """
        self.console.print("".join(r for r in self.riches))

    @staticmethod
    def multiprint(rss: list[RichString]):
        """ Print content of multiple RichStrings at once """
        for rs in rss:
            rs.print()

    def __str__(self) -> str:
        """ Return non-rich string """
        return "".join(self.strings)


class Table:

    def __init__(self):
        self._width:       int = None  # Number of elements in each row. Set when first row or header added
        self._header:      list[Any] = list()  # Header elements
        self._rows:        list[list[Any]] = list()   # All non-header rows
        self._left_aligns: list[Iterable[bool]] = list()  # True for left align, False for right align
        self._vlines:      set[int] = set()  # Row indexes that are followed by a vertical line

    def _set_and_check_width(self, row: list[Any]):
        if self._width is not None and len(row) != self._width:
            raise ValueError("Given row has %i elements, but width is %i" % (len(row), self._width))
        if self._width is None:
            self._width = len(row)

    def add_header(self, header: list[Any]):
        self._set_and_check_width(header)
        self._header = header

    def add_row(self, row: list[Any], left_align: Iterable[bool]=None):
        self._set_and_check_width(row)
        self._rows.append(row)
        self._left_aligns.append(left_align or [True] * self._width)

    def add_vline(self):
        self._vlines.add(len(self._rows)-1)

    @staticmethod
    def _format_element(element: Any, width: int, left_align: bool) -> str:
        element = str(element)
        if left_align:
            return element + " " * (width - len(element))
        else:
            return " " * (width - len(element)) + element

    def __str__(self) -> str:
        all_rows = [self._header, *self._rows] if self._header else self._rows
        widths = [max(len(str(all_rows[i][j])) for i in range(len(all_rows))) for j in range(self._width)]
        vline = "+".join(
            "-" * (width + 1 + (0 < i < self._width-1)) for i, width in enumerate(widths)
        )
        strs = list()
        if self._header:
            strs.append(" | ".join(
                self._format_element(elem, width, True) for elem, width in zip(self._header, widths)
            ))
            strs.append(vline)
        for i, (row, left_align) in enumerate(zip(self._rows, self._left_aligns)):
            strs.append(" | ".join(
                self._format_element(elem, width, la) for elem, width, la in zip(row, widths, left_align)
            ))
            if i in self._vlines:
                strs.append(vline)
        return "\n".join(strs)
