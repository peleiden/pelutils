"""JSON persistence for values that plain ``json`` and even ``pydantic`` cannot handle.

Saving experiment results, configs, or checkpoints to JSON usually means one of two
compromises: manually converting numpy arrays, tensors, and other objects into
JSON-friendly forms first, or reaching for ``pickle`` and ending up with an opaque binary
blob. :class:`UniversalJsonModel` removes the choice — it is a ``pydantic.BaseModel`` whose
``save``/``load`` methods serialise *any* attribute: JSON-native values stay plain and
human-readable, while anything else (numpy arrays, torch tensors, arbitrary objects) is
pickled and base64-encoded inline. The output stays a single, diffable JSON file you can
open and read.

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

The module also exposes :func:`pretty_json`, a compact-but-readable formatter that keeps
short containers on one line and bin-packs long primitive lists, and JSONL helpers
(:func:`jsonl_dump`, :func:`jsonl_load`, and their string variants) for files where each
line is its own JSON object.

.. warning::

    Loading pickles executes arbitrary code, so never ``load`` data from an untrusted source.
"""

from ._jsonl import jsonl_dump, jsonl_dumps, jsonl_load, jsonl_loads
from ._pretty_json import pretty_json
from ._universal_json_model import UniversalJsonModel

__all__ = ("UniversalJsonModel", "jsonl_dump", "jsonl_dumps", "jsonl_load", "jsonl_loads", "pretty_json")
