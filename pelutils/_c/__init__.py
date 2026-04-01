"""Utilities for pelutils C api, including a helpful way of passing numpy arrays and torch tensors to C."""

from __future__ import annotations

from typing import cast

import numpy as np

from pelutils.types import AnyArray

try:
    import torch

    _has_torch = True
except ModuleNotFoundError:
    _has_torch = False


# Data pointer, num dims, dimensions pointer, strides pointer
ArrayArgs = tuple[int, int, int, int]


def get_array_c_args(arr: AnyArray | torch.Tensor) -> ArrayArgs:
    if _has_torch and isinstance(arr, torch.Tensor):  # pyright: ignore[reportPossiblyUnboundVariable]
        arr = arr.numpy()
    # Tell the type checker that arr for sure is AnyArray
    # Not applied directly to arr.numpy() above as torch is possibly unbound, making the poor checker confused
    arr = cast(AnyArray, arr)

    dims = np.array(arr.shape, dtype=np.uint)
    ndim = len(dims)
    strides = np.array(arr.strides, dtype=np.uint)

    return arr.ctypes.data, ndim, dims.ctypes.data, strides.ctypes.data
