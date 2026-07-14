import sys
from pathlib import Path

# Make pelutils importable for autodoc
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pelutils import __version__ as release

version = ".".join(release.split(".")[:2])
project = "pelutils"
author = "asgerius"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",          # links to source
    "sphinx.ext.intersphinx",       # cross-links to other projects' docs
]

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "undoc-members": True,
}


def skip_reexported_top_level_members(app, what, name, obj, skip, options):
    """Avoid duplicate API objects from pelutils's convenience re-exports."""
    module = app.env.temp_data.get("autodoc:module")
    if module == "pelutils" and getattr(obj, "__module__", None) != "pelutils":
        return True
    return skip


def setup(app):
    """Configure autodoc event handlers."""
    app.connect("autodoc-skip-member", skip_reexported_top_level_members)

html_theme = "furo"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
