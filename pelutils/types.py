from typing import Any

import numpy as np
import numpy.typing as npt

# Common numpy types
AnyArray = npt.NDArray[Any]  # pyright: ignore[reportExplicitAny]
BoolArray = npt.NDArray[np.bool_]
ComplexArray = npt.NDArray[np.complexfloating[Any]]  # pyright: ignore[reportExplicitAny, reportInvalidTypeArguments]
FloatArray = npt.NDArray[np.floating[Any]]  # pyright: ignore[reportExplicitAny]
IntArray = npt.NDArray[np.integer[Any]]  # pyright: ignore[reportExplicitAny]
