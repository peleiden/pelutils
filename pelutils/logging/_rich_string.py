import re

from rich.color import ANSI_COLOR_NAMES
from rich.console import Console
from typing_extensions import override

_stdout_console = Console(highlight=False)
_stderr_console = Console(highlight=False, stderr=True)


class RichString:
    """Class used for combining normal strings and rich strings.

    This allows for printing and logging without rich syntax causing issues.
    """

    _open_tag_regex = re.compile("(%s)" % "|".join(r"\[" + c + r"\]" for c in ANSI_COLOR_NAMES))  # noqa: UP031
    _close_tag_regex_1 = re.compile(r"\\(\[\/.*\])")
    _close_tag_regex_2 = re.compile(r"(\[\/.*\])")

    def __init__(self, stderr: bool = False):
        self.strings: list[str] = list()  # Normal strings
        self.riches: list[str] = list()  # Corresponding strings with rich syntax
        self.console = _stderr_console if stderr else _stdout_console

    def add_string(self, s: str, rich: str | None = None):
        """Add a new string and optionally a rich string equivalent."""
        if rich is None:
            # Escape beginning brackets to prevent accidental formatting when printing
            rich = re.sub(self._open_tag_regex, r"\\\1", s)
            rich = re.sub(self._close_tag_regex_1, r"\1", rich)
            rich = re.sub(self._close_tag_regex_2, r"\\\1", rich)
        self.strings.append(s)
        self.riches.append(rich)

    def print(self):
        """Print rich text."""
        self.console.print("".join(r for r in self.riches))

    @staticmethod
    def multiprint(rss: "list[RichString]"):
        """Print content of multiple RichStrings at once."""
        for rs in rss:
            rs.print()

    @override
    def __str__(self) -> str:
        """Return non-rich string."""
        return "".join(self.strings)
