"""Readable type aliases for numpy arrays, so you never spell out a dtype generic by hand.

Annotating an array properly with ``numpy.typing`` means writing out the dtype generic
every time — ``npt.NDArray[np.floating[Any]]`` for a float array — which is verbose,
easy to get subtly wrong, and clutters otherwise simple signatures. These aliases give
each common dtype a plain, self-explanatory name so your annotations stay readable while
your type checker still verifies the intended dtype.

Quick start
-----------

.. code-block:: python

    from pelutils.types import BoolArray, FloatArray, IntArray

    def process(features: FloatArray, labels: IntArray, mask: BoolArray): ...

Aliases are provided for each common numpy dtype: :data:`AnyArray`, :data:`BoolArray`,
:data:`BytesArray`, :data:`ComplexArray`, :data:`FloatArray`, :data:`IntArray`,
:data:`ObjectArray`, :data:`StringArray`, and :data:`StructuredArray`.
"""

from ._types import AnyArray, BoolArray, BytesArray, ComplexArray, FloatArray, IntArray, ObjectArray, StringArray, StructuredArray

__all__ = ("AnyArray", "BoolArray", "BytesArray", "ComplexArray", "FloatArray", "IntArray", "ObjectArray", "StringArray", "StructuredArray")
