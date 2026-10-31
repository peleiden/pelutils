import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

from pelutils.logging import Logger


@pytest.fixture(scope="module")
def llms() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "docs" / "source" / "_llms.py"
    spec = importlib.util.spec_from_file_location("_llms", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_llms"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def full_text(llms: ModuleType) -> str:
    return llms.full_text()


def _section(text: str, heading: str) -> str:
    """Return the text between a heading and the next heading, ignoring comments in code blocks."""
    out = []
    in_section = in_code = False
    for line in text.split("\n"):
        in_code ^= line.startswith("```")
        if not in_code and line.startswith("#"):
            if in_section:
                break
            in_section = line.split(" ", 1)[1] == heading
        elif in_section:
            out.append(line)
    assert out, heading
    return "\n".join(out)


def test_rst_to_markdown(llms: ModuleType):
    rst = """Summary with :class:`Logger`, :meth:`~pelutils.logging.Logger.configure` and ``code``.

Quick start
-----------

    .. code-block:: python

        # A ``literal`` stays untouched in code
        log(":class:`x`")

    After the block.

.. warning::
    Careful with :func:`f`.

Parameters
----------
x : int
    Value."""
    assert (
        llms.rst_to_markdown(rst)
        == """Summary with `Logger`, `~pelutils.logging.Logger.configure` and `code`.

**Quick start**

```python
# A ``literal`` stays untouched in code
log(":class:`x`")
```

    After the block.

**Warning:** Careful with `f`.

**Parameters**
x : int
    Value.""".replace("`~pelutils.logging.Logger.configure`", "`pelutils.logging.Logger.configure`")
    )


def test_full_text_is_markdown(full_text: str):
    assert not re.search(r":(class|meth|func|data|attr):`", full_text)
    assert not re.search(r"^\s*\.\. [\w-]+::", full_text, re.MULTILINE)
    assert not re.search(r"^\s*(-{3,}|={3,})\s*$", full_text, re.MULTILINE)
    assert full_text.count("\n```") % 2 == 0


def test_full_text_contains_every_public_object(llms: ModuleType, full_text: str):
    for name, module in llms.public_modules().items():
        assert f"\n### pelutils.{name}\n" in full_text
        for member in module.__all__:
            assert f"\n#### pelutils.{name}.{member}\n" in full_text


def test_full_text_excludes_project_information(full_text: str):
    for heading in ("## Development", "## Updating and releasing", "## Coding agents"):
        assert f"\n{heading}\n" not in full_text
    assert "[![" not in full_text
    assert "## Logging" in full_text


def test_full_text_excludes_private_paths_and_legacy(full_text: str):
    assert not re.search(r"pelutils\.\w+\._", full_text)
    assert "pelutils.legacy" not in full_text


def test_full_text_excludes_external_inherited_members(full_text: str):
    assert "UniversalJsonModel.model_dump_json" not in full_text
    assert "UniversalJsonModel.save" in full_text
    assert "Also inherits from `pydantic.BaseModel`." in _section(full_text, "pelutils.serialization.UniversalJsonModel")


def test_full_text_documents_callable_instance_and_enum(full_text: str):
    assert "__call__(*tolog" in _section(full_text, "pelutils.logging.Logger.__call__")
    log_section = _section(full_text, "pelutils.logging.log")
    assert "global logging instance" in log_section
    assert f"`{Logger.__name__}`" in log_section
    assert "LogLevels.DEBUG = 0" in _section(full_text, "pelutils.logging.LogLevels")


def test_full_text_describes_aliases_and_readable_signatures(full_text: str):
    assert "numpy.floating" in _section(full_text, "pelutils.types.FloatArray")
    assert "RequiredArg | OptionalArg | Flag" in _section(full_text, "pelutils.job_parser.ArgumentTypes")
    assert "array_bytes(x: ArrayLike) -> int" in _section(full_text, "pelutils.array.array_bytes")
    assert "(self" not in _section(full_text, "pelutils.logging.Logger.configure")


def test_full_text_is_independent_of_build_machine(full_text: str):
    assert "hardware_info()" not in full_text
    assert not re.search(r" at 0x[0-9a-fA-F]+", full_text)
    assert "<class '" not in full_text
    assert "chunksize: int = io.DEFAULT_BUFFER_SIZE" in _section(full_text, "pelutils.misc.reverse_line_iterator")
    assert "test_dir: Path" in _section(full_text, "pelutils.tests.UnitTestCollection.test_dir")
    assert "is_linux: bool" in _section(full_text, "pelutils.misc.OS.is_linux")


@pytest.mark.parametrize(
    ("baseurl", "expected"),
    [
        ("https://example.com/en/stable/", "(https://example.com/en/stable/llms-full.txt)"),
        ("", "(llms-full.txt)"),
    ],
)
def test_index_links(llms: ModuleType, baseurl: str, expected: str):
    assert expected in llms.index_text(baseurl)


def test_index_lists_modules_and_exports(llms: ModuleType):
    index = llms.index_text("https://example.com/")
    assert index.startswith("# pelutils\n\n> ")
    assert "\n## Documentation\n" in index
    for name, module in llms.public_modules().items():
        assert f"- [pelutils.{name}](https://example.com/api/pelutils.{name}.html): " in index
        for member in module.__all__:
            assert f"`{member}`" in index
