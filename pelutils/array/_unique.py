from __future__ import annotations

from typing import TypeVar

import _pelutils_c as _c
import numpy as np
import numpy.typing as npt

import pelutils._c as c_utils
from pelutils.types import AnyArray

_ArrayT = TypeVar("_ArrayT", bound=AnyArray)


def unique(  # noqa: PLR0913
    array: npt.ArrayLike,
    *,
    return_index: bool = False,
    return_inverse: bool = False,
    return_counts: bool = False,
    return_groups: bool = False,
    axis: int = 0,
):
    """Return unique elements in a given numpy array.

    This function works very similar to ``np.unique``, but it runs in linear time, making it significantly faster
    for large arrays. Unlike with ``np.unique``, the returned unique values are unsorted. Because of this, it can
    also be used for detecting uniqueness along axes when ordering along the respective axes matters.

    With ``return_groups``, the last returned value is a list with an array for each unique value of all the indices at
    which it occurs in ascending order. The arrays are views of the same buffer. Each array has a memory overhead, so
    with many millions of unique values, consider using ``return_inverse`` instead.
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
    inverse = np.empty(len(array), dtype=np.int64) if return_inverse or return_groups else None
    counts = np.empty(len(array), dtype=np.int64) if return_counts or return_groups else None

    array_args = c_utils.ArrayArgs(array)
    c = _c.unique(
        array_args.array_ptr,
        array_args.ndim,
        array_args.dims_ptr,
        array_args.strides_ptr,
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
    ret: list[AnyArray | list[npt.NDArray[np.int64]]] = [array]
    if return_index:
        ret.append(index)
    if return_inverse:
        assert inverse is not None
        ret.append(inverse)
    if counts is not None:
        counts = counts[index]
    if return_counts:
        assert counts is not None
        ret.append(counts)
    if return_groups:
        assert inverse is not None
        assert counts is not None
        ret.append(_groups(inverse, counts))

    return tuple(ret) if len(ret) > 1 else ret[0]


def _groups(inverse: npt.NDArray[np.int64], counts: npt.NDArray[np.int64]) -> list[npt.NDArray[np.int64]]:
    """Build an array of indices for each unique value from the inverse and the counts."""
    order = np.empty(len(inverse), dtype=np.int64)
    stops = np.cumsum(counts)
    starts = stops - counts
    # The C function uses its starts as write positions, so it needs its own copy
    positions = starts.copy()
    _c.unique_groups(len(inverse), inverse.ctypes.data, positions.ctypes.data, order.ctypes.data)
    return [order[start:stop] for start, stop in zip(starts.tolist(), stops.tolist(), strict=True)]
