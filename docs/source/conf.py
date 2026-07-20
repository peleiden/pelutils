import re
import sys
from pathlib import Path

# Make pelutils importable for autodoc
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pelutils import __version__ as release

version = ".".join(release.split(".")[:2])
project = "pelutils"
author = "asgerius"

# Defining this reduces the amount of automatic type expansion in the docs
# Without this, some function signatures become practically unreadable
autodoc_type_aliases = {
    "npt.ArrayLike": "ArrayLike",
    "Callable": "Callable",
    "AnyArray": "AnyArray",
    "BoolArray": "BoolArray",
    "BytesArray": "BytesArray",
    "ComplexArray": "ComplexArray",
    "FloatArray": "FloatArray",
    "IntArray": "IntArray",
    "ObjectArray": "ObjectArray",
    "StringArray": "StringArray",
    "StructuredArray": "StructuredArray",
}

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",  # links to source
    "sphinx.ext.intersphinx",  # cross-links to other projects' docs
]

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "undoc-members": True,
}


def fix_type_alias_forward_refs(app, what, name, obj, options, signature, return_annotation):
    """Remove TypeAliasForwardRef which appears in nested types with type aliases."""

    def fix(value: str | None):
        if value is None:
            return None
        return re.sub(
            r"TypeAliasForwardRef\(['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\)",
            r"\1",
            value,
        )

    return fix(signature), fix(return_annotation)


def skip_reexported_top_level_members(app, what, name, obj, skip, options):
    """Avoid duplicate API objects from pelutils's convenience re-exports."""
    module = app.env.temp_data.get("autodoc:module")
    if module == "pelutils" and getattr(obj, "__module__", None) != "pelutils":
        return True
    return skip


def setup(app):
    """Configure autodoc event handlers."""
    app.connect("autodoc-skip-member", skip_reexported_top_level_members)
    app.connect("autodoc-process-signature", fix_type_alias_forward_refs)


html_theme = "furo"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
