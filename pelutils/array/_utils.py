import ctypes

import numpy as np
import numpy.typing as npt

from pelutils.misc._conditional_import import import_torch

torch = import_torch()


def array_ptr(arr: npt.ArrayLike) -> ctypes.c_void_p:
    """Return a pointer to a numpy array or torch tensor which can be used to interact with it in low-level languages like C/C++/Rust.

    This function is mostly useful when not using Python's C api and instead interfacing with .so files directly with ctypes.
    """
    if torch is not None and isinstance(arr, torch.Tensor):
        return ctypes.c_void_p(arr.data_ptr())
    if not isinstance(arr, np.ndarray):
        raise TypeError(f"Array should be of type np.ndarray or torch.Tensor, not {type(arr)}")
    if not arr.flags.c_contiguous:
        raise ValueError("Array must be C-contiguous")
    return ctypes.c_void_p(arr.ctypes.data)


def array_bytes(x: npt.ArrayLike) -> int:
    """Calculate the size of a numpy array or torch tensor in bytes."""
    if torch is not None and isinstance(x, torch.Tensor):
        x = x.numpy()
    if isinstance(x, np.ndarray):
        return x.nbytes
    raise TypeError(f"`x` of type {type(x)} is not a numpy array or torch tensor")
