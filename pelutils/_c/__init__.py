"""Utilities for pelutils C api, including a helpful way of passing numpy arrays and torch tensors to C."""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
import numpy.typing as npt

from pelutils.misc._conditional_import import import_torch
from pelutils.types import AnyArray as AnyArray

torch = import_torch()


# Data pointer, num dims, dimensions pointer, strides pointer
class ArrayArgs(NamedTuple):
    array_ptr: int
    ndim: int
    dims_ptr: int
    strides_ptr: int


def get_array_c_args(arr: npt.ArrayLike) -> ArrayArgs:
    if torch is not None and isinstance(arr, torch.Tensor):
        arr = arr.numpy()
    if not isinstance(arr, np.ndarray):
        raise TypeError(f"Array cannot be of type {type(arr)}")

    dims = np.array(arr.shape, dtype=np.uint)
    ndim = len(dims)
    strides = np.array(arr.strides, dtype=np.uint)

    return ArrayArgs(arr.ctypes.data, ndim, dims.ctypes.data, strides.ctypes.data)
