"""Utilities for pelutils C api, including a helpful way of passing numpy arrays and torch tensors to C."""

from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt

from pelutils._misc.conditional_import import import_torch
from pelutils.types import AnyArray

torch = import_torch()


# Data pointer, num dims, dimensions pointer, strides pointer
ArrayArgs = tuple[int, int, int, int]


def get_array_c_args(arr: npt.ArrayLike) -> ArrayArgs:
    if torch is not None and isinstance(arr, torch.Tensor):
        arr = arr.numpy()
    # Tell the type checker that arr for sure is AnyArray
    # Not applied directly to arr.numpy() above as torch is possibly unbound, making the poor checker confused
    arr = cast(AnyArray, arr)

    dims = np.array(arr.shape, dtype=np.uint)
    ndim = len(dims)
    strides = np.array(arr.strides, dtype=np.uint)

    return arr.ctypes.data, ndim, dims.ctypes.data, strides.ctypes.data
