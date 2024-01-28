from __future__ import annotations
from typing import Iterable

import numpy as np
try:
    import torch
    _has_torch = True
except ModuleNotFoundError:
    _has_torch = False

import _pelutils_c as _c
import pelutils._c as _c_utils


def unique(
    array: np.ndarray, *,
    return_index=False,
    return_inverse=False,
    return_counts=False,
    axis: int=0,
) -> np.ndarray | Iterable[np.ndarray]:
    """ Similar to np.unique, but in linear time and returns unsorted. """
    if not array.size:
        raise ValueError("Array must be non-empty")

    if axis:
        axes = list(range(len(array.shape)))
        axes[0] = axis
        axes[axis] = 0
        array = array.transpose(axes)
    if not array.flags["C_CONTIGUOUS"]:
        array = np.ascontiguousarray(array)

    index   = np.empty(len(array), dtype=int)
    inverse = np.empty(len(array), dtype=int) if return_inverse else None
    counts  = np.empty(len(array), dtype=int) if return_counts  else None

    c = _c.unique(
        *_c_utils.get_array_c_args(array),
        index.ctypes.data,
        inverse.ctypes.data if return_inverse else -1,
        counts.ctypes.data if return_counts else -1,
    )

    index = index[:c]
    if axis:
        array = array[index]
        array = np.ascontiguousarray(array.transpose(axes))
    else:
        array = array[index]
    ret = [array]
    if return_index:
        ret.append(index)
    if return_inverse:
        ret.append(inverse)
    if return_counts:
        # pylint: disable=unsubscriptable-object
        ret.append(counts[index])
    return tuple(ret) if len(ret) > 1 else ret[0]

def tensor_bytes(x: np.ndarray | torch.Tensor) -> int:
    """ Calculates the size of a numpy array or torch tensor in bytes. """
    if isinstance(x, np.ndarray):
        return x.nbytes
    elif _has_torch and isinstance(x, torch.Tensor):
        return x.element_size() * x.numel()
    else:
        raise TypeError("Unable to calculate the number of bytes of a tensor with type %s" % type(x))
