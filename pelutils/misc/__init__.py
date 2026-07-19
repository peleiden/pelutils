"""Standalone helpers that each solve one small, recurring annoyance.

Every project accumulates the same handful of little utilities —
a way to pretty-print a table, a check for which OS you are on, the current git commit —
and rewriting them each time is tedious and error-prone. This module is the grab-bag for
those: each helper is self-contained and useful on its own, so import only what you need.

Main inclusions are :class:`Table` for aligned text tables that also export to LaTeX via
:meth:`Table.to_latex`; :class:`OS` and :data:`hardware_info` for describing the machine
the code runs on; :func:`git_repo_info` for the repository and commit currently executing;
:func:`array_bytes`/:func:`array_ptr` for low-level array introspection; and small file
and dict helpers such as :func:`reverse_line_iterator` and :func:`except_keys`.
"""

from pelutils.misc._files import reverse_line_iterator
from pelutils.misc._git import git_repo_info
from pelutils.misc._misc import except_keys
from pelutils.misc._platform import OS, UnsupportedOS, hardware_info
from pelutils.misc._table import Table

__all__ = (
    "OS",
    "Table",
    "UnsupportedOS",
    "except_keys",
    "git_repo_info",
    "hardware_info",
    "reverse_line_iterator",
)
