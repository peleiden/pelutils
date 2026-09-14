"""JSON persistence for Pydantic models containing non-JSON values.

JSON is useful when the structure of a file should remain inspectable, but it does not represent
values such as NumPy arrays, tensors, or arbitrary Python objects. ``UniversalJsonModel``
keeps JSON-native values in the document and stores unsupported field values as base64-encoded
pickle payloads. This preserves a readable JSON envelope without requiring callers to write
converters for every field type.

The usual interface is :meth:`UniversalJsonModel.save` and
:meth:`UniversalJsonModel.load`. ``save`` creates missing parent directories and writes the model to a JSON
file; ``load`` reconstructs the model from that file. Use :meth:`UniversalJsonModel.to_json_dict`
and :meth:`UniversalJsonModel.from_json_dict` when the serialized representation should be nested
inside another structure or handled by another storage layer.

For standalone dictionaries and lists, ``pretty_json`` converts Python objects to pretty-formatted JSON,
filling the same role as ``json.dumps``, but often making the resulting JSON more readable.
JSONL helpers handle files containing multiple JSON records separated by newlines.

Quick start
-----------

.. code-block:: python

    import numpy as np
    from pelutils.serialization import UniversalJsonModel
    from pelutils.types import FloatArray

    class Result(UniversalJsonModel):
        accuracy: float
        predictions: FloatArray   # numpy arrays are handled automatically

    result = Result(accuracy=0.97, predictions=np.arange(5, dtype=np.float16))
    result.save("results/run-1.json")
    result = Result.load("results/run-1.json")

This format is intended for trusted application data such as experiment results and cached state,
not as a language-neutral interchange format. Pickle payloads are Python-specific, and loading
them can execute arbitrary code. Use a format with an explicit schema and safe decoder when data
comes from outside the application.

.. warning::

    ``UniversalJsonModel.load`` and the pickle fallback execute code while loading. Never load
    files from an untrusted source.
"""

from ._jsonl import jsonl_dump, jsonl_dumps, jsonl_load, jsonl_loads
from ._pretty_json import pretty_json
from ._universal_json_model import UniversalJsonModel

__all__ = ("UniversalJsonModel", "jsonl_dump", "jsonl_dumps", "jsonl_load", "jsonl_loads", "pretty_json")
