from typing import Any

import numpy as np
import numpy.typing as npt

# Common numpy types
AnyArray = npt.NDArray[Any]  # pyright: ignore[reportExplicitAny]
FloatArray = npt.NDArray[np.floating[Any]]  # pyright: ignore[reportExplicitAny]
IntArray = npt.NDArray[np.integer[Any]]  # pyright: ignore[reportExplicitAny]
