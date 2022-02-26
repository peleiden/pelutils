from __future__ import annotations
from typing import Callable, Generator, Iterable
import functools

import numpy as np

_import_error = ModuleNotFoundError("To use the ds submodule, you must install pelutils[ds]")

try:
    import torch
except ModuleNotFoundError as e:
    raise _import_error from e

from pelutils import c_ptr
import _pelutils_c as _c


def unique(
    array: np.ndarray, *,
    return_index=False,
    return_inverse=False,
    return_counts=False,
    axis: int=0,
) -> np.ndarray | Iterable[np.ndarray]:
    """ Similar to np.unique, but in linear time and returns unsorted """
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

    c = _c.unique(array, index, inverse, counts)

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

def no_grad(fun: Callable) -> Callable:
    """ Decorator for running functions without pytorch tracking gradients, e.g.
    ```
    @no_grad
    def feed_forward(x):
        return net(x)
    ``` """
    functools.wraps(fun)
    def wrapper(*args, **kwargs):
        with torch.no_grad():
            return fun(*args, **kwargs)
    return wrapper
