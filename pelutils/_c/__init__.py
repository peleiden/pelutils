"""Utilities for pelutils C api, including a helpful way of passing numpy arrays and torch tensors to C."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from pelutils.misc._conditional_import import import_torch
from pelutils.types import AnyArray as AnyArray

torch = import_torch()


# Data pointer, num dims, dimensions pointer, strides pointer
class ArrayArgs:
    def __init__(self, arr: npt.ArrayLike):
        if torch is not None and isinstance(arr, torch.Tensor):
            arr = arr.numpy()
        if not isinstance(arr, np.ndarray):
            raise TypeError(f"Array cannot be of type {type(arr)}")
        # Store attributes on self to prevent garbage collector cleaning them up until the object no longer exists
        self._arr = arr
        self._dims = np.array(self._arr.shape, dtype=np.uint64)
        self._strides = np.array(self._arr.strides, dtype=np.uint64)

        self.array_ptr = self._arr.ctypes.data
        self.ndim = len(self._dims)
        self.dims_ptr = self._dims.ctypes.data
        self.strides_ptr = self._strides.ctypes.data
