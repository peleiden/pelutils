from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

# Common numpy types
# If adding any new ones here, make sure to also add them to docs/source/api/conf.py
# Internal modules which use them (or npt.ArrayLike) must have `from __future__ import annotations`
AnyArray: TypeAlias = npt.NDArray[Any]  # pyright: ignore[reportExplicitAny]
BoolArray: TypeAlias = npt.NDArray[np.bool_]
BytesArray: TypeAlias = npt.NDArray[np.bytes_]
ComplexArray: TypeAlias = npt.NDArray[np.complexfloating[Any]]  # pyright: ignore[reportExplicitAny]
FloatArray: TypeAlias = npt.NDArray[np.floating[Any]]  # pyright: ignore[reportExplicitAny]
IntArray: TypeAlias = npt.NDArray[np.integer[Any]]  # pyright: ignore[reportExplicitAny]
ObjectArray: TypeAlias = npt.NDArray[np.object_]
StringArray: TypeAlias = npt.NDArray[np.str_]
StructuredArray: TypeAlias = npt.NDArray[np.void]
