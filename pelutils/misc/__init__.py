"""Miscellaenous functionality is stored in this module and is exported top-level."""

from pelutils.misc._array import array_bytes, array_ptr, unique
from pelutils.misc._files import reverse_line_iterator
from pelutils.misc._git import git_repo_info
from pelutils.misc._misc import except_keys
from pelutils.misc._platform import OS, UnsupportedOS, hardware_info
from pelutils.misc._table import Table

__all__ = (
    "OS",
    "Table",
    "UnsupportedOS",
    "array_bytes",
    "array_ptr",
    "except_keys",
    "git_repo_info",
    "hardware_info",
    "reverse_line_iterator",
    "unique",
)
