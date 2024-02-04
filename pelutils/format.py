from __future__ import annotations
from typing import Any, Iterable, Optional
import os
import re

from rich.color import ANSI_COLOR_NAMES
from rich.console import Console


_stdout_console = Console(highlight=False)
_stderr_console = Console(highlight=False, stderr=True)

class RichString:

    """
    Class used for combining normal strings and rich strings
    This allows for printing and logging without rich syntax causing issues
    """

    _open_tag_regex = re.compile("(%s)" % "|".join(r"\[" + c + r"\]" for c in ANSI_COLOR_NAMES))
    _close_tag_regex_1 = re.compile(r"\\(\[\/.*\])")
    _close_tag_regex_2 = re.compile(r"(\[\/.*\])")

    def __init__(self, stderr=False):
        self.strings: list[str] = list()  # Normal strings
        self.riches:  list[str] = list()  # Corresponding strings with rich syntax
        self.console = _stderr_console if stderr else _stdout_console

    def add_string(self, s: str, rich: str=None):
        """ Add a new string and optionally a rich string equivalent """
        if rich is None:
            # Escape beginning brackets to prevent accidental formatting when printing
            rich = re.sub(self._open_tag_regex, r"\\\1", s)
            rich = re.sub(self._close_tag_regex_1, r"\1", rich)
            rich = re.sub(self._close_tag_regex_2, r"\\\1", rich)
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
        self._left_aligns: list[list[bool]] = list()  # True for left align, False for right align
        self._hlines:      set[int] = set()  # Row indexes that are followed by a horizontal line

    def _set_and_check_width(self, row: list[Any]):
        if self._width is not None and len(row) != self._width:
            raise ValueError("Given row has %i elements, but width is %i" % (len(row), self._width))
        if self._width is None:
            self._width = len(row)

    def add_header(self, header: list[Any]):
        self._set_and_check_width(header)
        self._header = header

    def add_row(self, row: list[Any], left_align: Optional[Iterable[bool]]=None):
        """ Add a row to the table. left_align is a boolean iterable of the same length
        as row indicating whether each element is right or left aligned. If None, the
        first element is left aligned and the rest right aligned. """
        self._set_and_check_width(row)
        self._rows.append(row)
        if left_align is None:
            left_align = [False] * self._width
            left_align[0] = True
        else:
            left_align = list(left_align)

        if len(row) != len(left_align):
            raise ValueError("Number of row elements (%i) does not match number of left aligns (%i)" % (len(row), len(left_align)))

        self._left_aligns.append(left_align)

    def add_hline(self):
        self._hlines.add(len(self._rows)-1)

    def tex(self) -> str:
        """ Produces code for rendering the table in LaTeX. The code should go
        into a tabular environment. It assumes the booktabs package is used. """
        formatted = str(self)
        lines = formatted.splitlines()
        lines.insert(0, r"\toprule")
        lines.append(r"\bottomrule")

        for i, line in enumerate(lines):
            if re.match(r"^(-+\+)+-+$", line):
                lines[i] = r"\midrule"
            elif re.match(r"^(.+\|)+.+$", line):
                lines[i] = line.replace("|", "&") + r" \\"

        return os.linesep.join(lines)

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
        hline = "+".join(
            "-" * (width + 1 + (0 < i < self._width-1)) for i, width in enumerate(widths)
        )
        strs = list()
        if self._header:
            strs.append(" | ".join(
                self._format_element(elem, width, True) for elem, width in zip(self._header, widths)
            ))
            strs.append(hline)
        for i, (row, left_align) in enumerate(zip(self._rows, self._left_aligns)):
            strs.append(" | ".join(
                self._format_element(elem, width, la) for elem, width, la in zip(row, widths, left_align)
            ))
            if i in self._hlines:
                strs.append(hline)

        return os.linesep.join(strs)
