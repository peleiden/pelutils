""" Utilities for pelutils C api, including a helpful way of passing
numpy arrays and torch tensors to C. """
from __future__ import annotations

from typing import Tuple

import numpy as np
try:
    import torch
    _has_torch = True
except ModuleNotFoundError:
    _has_torch = False


# Data pointer, num dims, dimensions pointer, strides pointer
ArrayArgs = Tuple[int, int, int, int]

def get_array_c_args(arr: np.ndarray | torch.Tensor) -> ArrayArgs:
    if _has_torch and isinstance(arr, torch.Tensor):
        arr = arr.numpy()

    dims = np.array(arr.shape, dtype=np.uint)
    ndim = len(dims)
    strides = np.array(arr.strides, dtype=np.uint)

    return arr.ctypes.data, ndim, dims.ctypes.data, strides.ctypes.data
