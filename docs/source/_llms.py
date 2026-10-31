"""Generate llms.txt and llms-full.txt (https://llmstxt.org) from the README and the public API."""

import enum
import importlib
import inspect
import io
import pkgutil
import re
import textwrap
from functools import cached_property
from importlib.metadata import metadata
from pathlib import Path, PurePath
from types import GenericAlias, ModuleType, UnionType
from urllib.parse import urljoin

import numpy.typing as npt
from sphinx.pycode import ModuleAnalyzer

import pelutils
import pelutils.types

README = Path(__file__).resolve().parents[2] / "README.md"

# README sections which are about the project itself rather than about using the library
_EXCLUDED_README_SECTIONS = {"Coding agents", "Development", "Updating and releasing"}
_DOCUMENTED_DUNDERS = {"__call__", "__enter__", "__getitem__", "__iter__"}

_DIRECTIVE = re.compile(r"^(\s*)\.\. ([\w-]+)::\s*(.*)$")
_UNDERLINE = re.compile(r"^\s*(-{3,}|={3,}|~{3,})\s*$")
_ROLE = re.compile(r":\w+(?::\w+)?:`~?([^`]+)`")
_LITERAL = re.compile(r"``(.+?)``")
_PRIVATE_PATH = re.compile(r"\bpelutils(?:\.\w+)*?\._\w+\.")
_ENUM_REPR = re.compile(r"<(\w+\.\w+): [^>]+>")
_OBJECT_REPR = re.compile(r"<(?:function (\S+) at 0x[0-9a-fA-F]+|class '([^']+)')>")
_PLAIN_DATA = (bool, int, float, str, tuple, list, dict, set, frozenset)


def _inline_to_markdown(text: str) -> str:
    return _LITERAL.sub(r"`\1`", _ROLE.sub(r"`\1`", text))


def rst_to_markdown(text: str) -> str:
    """Convert the reStructuredText constructs used in docstrings to Markdown."""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if directive := _DIRECTIVE.match(line):
            indent, name, argument = directive.groups()
            i += 1
            body = []
            while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > len(indent)):
                body.append(lines[i])
                i += 1
            content = textwrap.dedent("\n".join(body)).strip("\n")
            if name == "code-block":
                out += [f"```{argument}", content, "```", ""]
            else:
                out += [f"**{name.capitalize()}:** {_inline_to_markdown(' '.join((argument, content)).strip())}", ""]
        elif line.strip() and i + 1 < len(lines) and _UNDERLINE.match(lines[i + 1]):
            out.append(f"**{_inline_to_markdown(line.strip())}**")
            i += 2
        else:
            out.append(_inline_to_markdown(line))
            i += 1
    return "\n".join(out).strip()


def public_modules() -> dict[str, ModuleType]:
    """Return every non-private submodule of pelutils which defines ``__all__``."""
    names = sorted(info.name for info in pkgutil.iter_modules(pelutils.__path__) if not info.name.startswith("_"))
    modules = {name: importlib.import_module(f"pelutils.{name}") for name in names}
    return {name: module for name, module in modules.items() if hasattr(module, "__all__")}


def _attribute_docs(module: ModuleType) -> dict[tuple[str, str], str]:
    """Return documentation comments of attributes in a module and its submodules, which are not available at runtime."""
    module_names = [module.__name__, *(f"{module.__name__}.{m.name}" for m in pkgutil.iter_modules(module.__path__))]
    docs = {}
    for module_name in module_names:
        for key, lines in ModuleAnalyzer.for_module(module_name).find_attr_docs().items():
            docs[key] = "\n".join(lines).strip()
    return docs


def _clean_type_text(text: str) -> str:
    """Shorten a stringified type to the names that are used in the public API."""
    text = text.replace(inspect.formatannotation(npt.ArrayLike), "ArrayLike").replace("npt.ArrayLike", "ArrayLike")
    for alias in pelutils.types.__all__:
        text = text.replace(inspect.formatannotation(getattr(pelutils.types, alias)), alias)
    text = _OBJECT_REPR.sub(lambda match: match.group(1) or match.group(2), text)
    return _ENUM_REPR.sub(r"\1", _PRIVATE_PATH.sub("", text))


class _Verbatim:
    """Annotation which is printed as is, as ``inspect.signature`` would otherwise quote strings."""

    def __init__(self, annotation: object):
        text = annotation if isinstance(annotation, str) else inspect.formatannotation(annotation)
        self.text = _clean_type_text(text)

    def __repr__(self) -> str:
        return self.text


def _signature(name: str, obj: object, *, is_method: bool = False, is_class: bool = False) -> str | None:
    """Return a readable signature, or ``None`` if the object has none, e.g. for some builtins."""
    try:
        signature = inspect.signature(obj)  # pyright: ignore[reportArgumentType]
    except (TypeError, ValueError):
        return None
    parameters = list(signature.parameters.values())
    if is_method and parameters:
        parameters = parameters[1:]
    # This default differs between Python versions, so its name is published instead of its value
    parameters = [p.replace(default=_Verbatim("io.DEFAULT_BUFFER_SIZE")) if p.default is io.DEFAULT_BUFFER_SIZE else p for p in parameters]
    empty = inspect.Signature.empty
    signature = signature.replace(
        parameters=[p.replace(annotation=empty if p.annotation is empty else _Verbatim(p.annotation)) for p in parameters],
        return_annotation=empty if is_class or signature.return_annotation is empty else _Verbatim(signature.return_annotation),
    )
    return _clean_type_text(f"{name}{signature}")


def _code(text: str) -> str:
    return f"```python\n{text}\n```"


def _section(level: int, path: str, *parts: str | None) -> str:
    return "\n\n".join([f"{'#' * level} {path}", *(part for part in parts if part)])


def _doc(obj: object) -> str | None:
    doc = inspect.getdoc(obj)
    return rst_to_markdown(doc) if doc else None


def _class_members(cls: type) -> dict[str, tuple[type, object]]:
    """Return public members of a class defined in pelutils along with the class defining them."""
    members = {}
    for base in cls.__mro__:
        if not base.__module__.startswith("pelutils."):
            continue
        for name, value in vars(base).items():
            is_public = not name.startswith("_") or name in _DOCUMENTED_DUNDERS
            if is_public and name not in members and not isinstance(value, enum.Enum):
                members[name] = (base, value)
        for name, annotation in inspect.get_annotations(base).items():
            if not name.startswith("_") and name not in members:
                members[name] = (base, _Verbatim(annotation))
    return members


def _member_section(level: int, path: str, name: str, base: type, value: object, attr_docs: dict) -> str:
    if isinstance(value, property | cached_property):
        getter = value.fget if isinstance(value, property) else value.func
        annotation = inspect.signature(getter).return_annotation  # pyright: ignore[reportArgumentType]
        declaration = name if annotation is inspect.Signature.empty else f"{name}: {_Verbatim(annotation)}"
        return _section(level, path, _code(declaration), _doc(value))
    attribute_doc = attr_docs.get((base.__name__, name))
    attribute_doc = rst_to_markdown(attribute_doc) if attribute_doc else None
    if isinstance(value, _Verbatim):
        return _section(level, path, _code(f"{name}: {value}"), attribute_doc)
    if isinstance(value, staticmethod):
        return _section(level, path, _code(f"@staticmethod\n{_signature(name, value.__func__) or name}"), _doc(value.__func__))
    if isinstance(value, classmethod):
        return _section(
            level, path, _code(f"@classmethod\n{_signature(name, value.__func__, is_method=True) or name}"), _doc(value.__func__)
        )
    if inspect.isroutine(value):
        return _section(level, path, _code(_signature(name, value, is_method=True) or name), _doc(value))
    if inspect.isclass(value):
        return _section(level, path, _code(f"class {name}"), _doc(value))
    # Values of class attributes may depend on the machine building the documentation, so only their types are published
    doc = attribute_doc or (_doc(value) if type(value).__module__.startswith("pelutils.") else None)
    type_name = "Path" if isinstance(value, PurePath) else type(value).__name__
    return _section(level, path, _code(f"{name}: {type_name}"), doc)


def _class_section(level: int, path: str, name: str, cls: type, attr_docs: dict, *notes: str | None, is_instance: bool = False) -> str:
    if is_instance:
        head = None
    elif issubclass(cls, enum.Enum):
        head = _code("\n".join(f"{cls.__name__}.{member.name} = {member.value!r}" for member in cls))
    else:
        head = _code(_signature(name, cls, is_class=True) or name)
    external_bases = [
        f"`{base.__module__.split('.')[0]}.{base.__name__}`"
        for base in cls.__bases__
        if base is not object and not base.__module__.startswith("pelutils.") and not issubclass(base, enum.Enum | BaseException)
    ]
    inherits = f"Also inherits from {', '.join(external_bases)}." if external_bases else None
    sections = [_section(level, path, *notes, head, inherits, _doc(cls))]
    for member_name, (base, value) in _class_members(cls).items():
        sections.append(_member_section(level + 1, f"{path}.{member_name}", member_name, base, value, attr_docs))
    return "\n\n".join(sections)


def _object_section(level: int, path: str, name: str, module: ModuleType, attr_docs: dict) -> str:
    obj = getattr(module, name)
    if inspect.isclass(obj):
        return _class_section(level, path, name, obj, attr_docs)
    if inspect.isroutine(obj):
        return _section(level, path, _code(_signature(name, obj) or name), _doc(obj))
    attribute_doc = attr_docs.get(("", name))
    attribute_doc = rst_to_markdown(attribute_doc) if attribute_doc else None
    if isinstance(obj, GenericAlias | UnionType):
        return _section(level, path, _code(f"{name} = {_PRIVATE_PATH.sub('', repr(obj))}"), attribute_doc)
    if isinstance(obj, _PLAIN_DATA):
        return _section(level, path, _code(f"{name} = {_clean_type_text(repr(obj))}"), attribute_doc)
    cls = type(obj)
    if cls.__name__ in module.__all__:
        return _section(level, path, attribute_doc, f"Instance of `{cls.__name__}`, documented in this module.")
    # The class is private, so the instance is the only place its documentation can appear. Its members
    # are described rather than its value, which depends on the machine building the documentation.
    return _class_section(level, path, name, cls, attr_docs, attribute_doc, is_instance=True)


def _readme_for_agents() -> str:
    """Return the README with badges and sections unrelated to using the library removed."""
    head, *sections = re.split(r"^(?=## )", README.read_text(encoding="utf-8"), flags=re.MULTILINE)
    head = "\n".join(line for line in head.split("\n") if not line.startswith("[!["))
    kept = [section for section in sections if section.split("\n")[0].removeprefix("## ") not in _EXCLUDED_README_SECTIONS]
    return re.sub(r"\n{3,}", "\n\n", "".join([head, *kept])).strip()


def _version_note() -> str:
    return f"This documents version {pelutils.__version__}."


def full_text() -> str:
    """Return the contents of llms-full.txt: The README followed by the documentation of the public API."""
    readme = _readme_for_agents().replace("# pelutils\n", f"# pelutils\n\n{_version_note()}\n", 1)
    sections = [readme, "## API reference"]
    for name, module in public_modules().items():
        sections.append(_section(3, f"pelutils.{name}", _doc(module)))
        attr_docs = _attribute_docs(module)
        for member in module.__all__:
            sections.append(_object_section(4, f"pelutils.{name}.{member}", member, module, attr_docs))
    return "\n\n".join(sections) + "\n"


def index_text(baseurl: str) -> str:
    """Return the contents of llms.txt. Links are absolute if a base URL is given."""
    package = metadata("pelutils")
    lines = [
        "# pelutils",
        "",
        f"> {package['Summary']}",
        "",
        f"{_version_note()} Install with `pip install pelutils`; it requires Python {package['Requires-Python']}. "
        "Everything is imported from its submodule, e.g. `from pelutils.logging import log`, as the package root "
        "only exports `__version__`. PyTorch is optional.",
        "",
        "## Documentation",
        "",
        f"- [Full documentation]({urljoin(baseurl, 'llms-full.txt')}): Usage guide and the public API in one file",
        "",
        "## Modules",
        "",
    ]
    for name, module in public_modules().items():
        summary = _inline_to_markdown((inspect.getdoc(module) or "").split("\n")[0])
        exports = ", ".join(f"`{member}`" for member in module.__all__)
        lines.append(f"- [pelutils.{name}]({urljoin(baseurl, f'api/pelutils.{name}.html')}): {summary} Exports {exports}.")
    return "\n".join(lines) + "\n"


def write_llms_txt(app, exception):
    """Write llms.txt and llms-full.txt next to the HTML output so they are published with the docs."""
    if exception is None and app.builder.name == "html":
        outdir = Path(app.outdir)
        (outdir / "llms.txt").write_text(index_text(app.config.html_baseurl), encoding="utf-8")
        (outdir / "llms-full.txt").write_text(full_text(), encoding="utf-8")
