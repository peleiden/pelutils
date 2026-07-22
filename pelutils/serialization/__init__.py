"""JSON persistence for values that plain ``json`` and even ``pydantic`` cannot handle.

Persisting data, whatever it may be, to disk usually usually comes down to a choice between
human-readable or not. If efficiency is not crucial, human-readable is preferable, but often
times, the data is not trivially serialisable to human-friendly formats. While ``pydantic``'s
``BaseModel.model_dump`` takes you some of the way, it falls short as soon as you introduce
data types which are not JSON-serialisable by default, making pickling the default choice and
ending up with an unreadable binary blob.

Even if all data is easily serialisable to a readable format, you still have to deal with all
the boilerplate of ensuring parent directories exist, and opening and closing files.

Enter :class:`UniversalJsonModel` — a ``pydantic.BaseModel`` whose
``save``/``load`` methods serialise/deserialise *any* attribute: JSON-native values stay plain and
human-readable, while anything else (numpy arrays, torch tensors, arbitrary objects) is
pickled and base64-encoded inline. The output is a single, easily readable JSON file.

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

The module also exposes :func:`pretty_json`, a function similar to the built-in `json.dumps`,
but which formats the given object to a pretty JSON string;
short containers stay on one line, and long primitive lists are packed across both the width and height
of the file.
JSONL helpers (:func:`jsonl_dump`, :func:`jsonl_load`, and their string variants) for files where each
line is its own JSON object are also provided.

.. warning::

    Loading pickles executes arbitrary code, so never ``load`` data from an untrusted source.
"""

from ._jsonl import jsonl_dump, jsonl_dumps, jsonl_load, jsonl_loads
from ._pretty_json import pretty_json
from ._universal_json_model import UniversalJsonModel

__all__ = ("UniversalJsonModel", "jsonl_dump", "jsonl_dumps", "jsonl_load", "jsonl_loads", "pretty_json")
