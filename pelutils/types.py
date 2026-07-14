from typing import Any

import numpy as np
import numpy.typing as npt

__all__ = ("AnyArray", "BoolArray", "BytesArray", "ComplexArray", "FloatArray", "IntArray", "ObjectArray", "StringArray")

# Common numpy types
AnyArray = npt.NDArray[Any]  # pyright: ignore[reportExplicitAny]
BoolArray = npt.NDArray[np.bool_]
BytesArray = npt.NDArray[np.bytes_]
ComplexArray = npt.NDArray[np.complexfloating[Any]]  # pyright: ignore[reportExplicitAny]
FloatArray = npt.NDArray[np.floating[Any]]  # pyright: ignore[reportExplicitAny]
IntArray = npt.NDArray[np.integer[Any]]  # pyright: ignore[reportExplicitAny]
ObjectArray = npt.NDArray[np.object_]
StringArray = npt.NDArray[np.str_]
