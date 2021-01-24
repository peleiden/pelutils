from __future__ import annotations
from typing import Any


class Table:

    def __init__(self):
        self.width: int = None  # Number of elements in each row. Set when first row or header added
        self.header: list[Any] = list()  # Header elements
        self.rows: list[list[Any]] = list()   # All non-header rows
        self.left_aligns: list[list[bool]] = list()  # True for left align, False for right align

    def _set_and_check_width(self, row: list[Any]):
        if self.width is not None and len(row) != self.width:
            raise ValueError("Given row has %i elements, but width is %i" % (len(row), self.width))
        if self.width is None:
            self.width = len(row)

    def add_header(self, header: list[Any]):
        self._set_and_check_width(header)
        self.header = header

    def add_row(self, row: list[Any], left_align: list[bool]=None):
        self._set_and_check_width(row)
        self.rows.append(row)
        self.left_aligns.append(left_align or [True] * self.width)

    @staticmethod
    def _format_element(element: Any, width: int, left_align: bool) -> str:
        element = str(element)
        if left_align:
            return element + " " * (width - len(element))
        else:
            return " " * (width - len(element)) + element

    def __str__(self) -> str:
        all_rows = [self.header, *self.rows] if self.header else self.rows
        widths = [max(len(str(all_rows[i][j])) for i in range(len(all_rows))) for j in range(self.width)]
        strs = list()
        if self.header:
            strs.append(" | ".join(
                self._format_element(elem, width, True) for elem, width in zip(self.header, widths)
            ))
            strs.append("+".join(
                "-" * (width+1+(0 < i < self.width-1)) for i, width in enumerate(widths)
            ))
        for row, left_align in zip(self.rows, self.left_aligns):
            strs.append(" | ".join(
                self._format_element(elem, width, la) for elem, width, la in zip(row, widths, left_align)
            ))
        return "\n".join(strs)
