from __future__ import annotations

from typing import TypeVar

import _pelutils_c as _c
import numpy as np
import numpy.typing as npt

import pelutils._c as c_utils
from pelutils.types import AnyArray

_ArrayT = TypeVar("_ArrayT", bound=AnyArray)


def unique(
    array: npt.ArrayLike,
    *,
    return_index: bool = False,
    return_inverse: bool = False,
    return_counts: bool = False,
    axis: int = 0,
):
    """Return unique elements in a given numpy array.

    This function works very similar to ``np.unique``, but it runs in linear time, making it significantly faster
    for large arrays. Unlike with ``np.unique``, the returned unique values are unsorted. Because of this, it can
    also be used for detecting uniqueness along axes when ordering along the respective axes matters.
    """
    array = np.asarray(array)
    if np.issubdtype(array.dtype, np.object_):
        raise TypeError(f"Unsupported array dtype {array.dtype}")

    if array.ndim == 0:
        raise ValueError("unique does not work for shapeless arrays")

    if axis:
        axes = list(range(len(array.shape)))
        axes[0] = axis
        axes[axis] = 0
        array = array.transpose(axes)
    else:
        axes = None
    if not array.flags["C_CONTIGUOUS"]:
        array = np.ascontiguousarray(array)

    index = np.empty(len(array), dtype=np.int64)
    inverse = np.empty(len(array), dtype=np.int64) if return_inverse else None
    counts = np.empty(len(array), dtype=np.int64) if return_counts else None

    c = _c.unique(
        *c_utils.get_array_c_args(array),
        index.ctypes.data,
        inverse.ctypes.data if inverse is not None else 0,
        counts.ctypes.data if counts is not None else 0,
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
        assert inverse is not None
        ret.append(inverse)
    if return_counts:
        assert counts is not None
        ret.append(counts[index])

    return tuple(ret) if len(ret) > 1 else ret[0]
