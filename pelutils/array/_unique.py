from __future__ import annotations

import math
import operator
import os
from typing import SupportsIndex, TypeVar

import _pelutils_c as _c
import numpy as np
import numpy.typing as npt

from pelutils.types import AnyArray

_ArrayT = TypeVar("_ArrayT", bound=AnyArray)

# Arrays with fewer elements than this are always processed on a single thread
_MIN_PARALLEL_SIZE = 2**18
# Maximum number of threads used when the number of threads is not explicitly chosen
_MAX_DEFAULT_THREADS = 8
# Elements of these sizes use a lookup table, which is fast enough on a single thread
_SERIAL_ELEMENT_SIZES = (1, 2)


def _available_cpus() -> int:
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0)) or 1
    return os.cpu_count() or 1


def _resolve_n_threads(n_threads: SupportsIndex | None) -> int:
    """Return the maximum number of threads, which is the available CPUs up to a limit if ``n_threads`` is not given."""
    if n_threads is not None:
        n_threads = operator.index(n_threads)
        if n_threads < 1:
            raise ValueError(f"n_threads must be at least 1, not {n_threads}")
        return n_threads
    return min(_available_cpus(), _MAX_DEFAULT_THREADS)


def _with_equal_nans(array: AnyArray) -> AnyArray:
    """Return the array with the same bytes for all NaNs, which is a copy if there are any NaNs."""
    if array.dtype.kind not in "fc":
        return array
    is_nan = np.isnan(array)
    if not is_nan.any():
        return array
    array = array.copy()
    array[is_nan] = np.nan
    return array


def unique(  # noqa: PLR0912, PLR0913
    array: npt.ArrayLike,
    *,
    return_index: bool = False,
    return_inverse: bool = False,
    return_counts: bool = False,
    return_groups: bool = False,
    axis: int = 0,
    n_threads: SupportsIndex | None = None,
):
    """Return unique elements in a given numpy array.

    This function works very similar to ``np.unique``, but it runs in linear time, making it significantly faster
    for large arrays. Unlike with ``np.unique``, the returned unique values are unsorted. Because of this, it can
    also be used for detecting uniqueness along axes when ordering along the respective axes matters.

    Values are returned in the order they first appear. Elements are equal if their bytes are equal, including any
    padding bytes, except that all NaNs in float and complex arrays are equal to each other. This takes a temporary
    copy of arrays containing NaNs, and a returned NaN keeps the bits of its first occurrence. ``0.0`` and ``-0.0`` are
    different, and NaNs in the fields of structured arrays have no special treatment.

    The results do not depend on the number of threads. The GIL is held during the computation, including when using
    multiple threads, so Python threads wait for it to finish. On free-threaded Python, the array must not be modified
    meanwhile.

    Parameters
    ----------
    array : npt.ArrayLike
        Array to find unique elements in.
    return_index : bool
        Also return the index of the first occurrence of each unique value.
    return_inverse : bool
        Also return the index in the unique values of each element.
    return_counts : bool
        Also return the number of occurrences of each unique value.
    return_groups : bool
        Also return a list with an array for each unique value of all the indices at which it occurs in ascending
        order. The arrays are views of the same buffer. Each array has a memory overhead, so with many millions of
        unique values, consider using ``return_inverse`` instead.
    axis : int
        Axis along which to find unique elements.
    n_threads : SupportsIndex | None
        Maximum number of threads. If not given, the number of available CPUs is used up to a maximum of 8.
        Small arrays use a single thread.

    Returns
    -------
    tuple | np.ndarray
        The unique values, followed by the requested arrays in the order of the parameters above. If only the unique
        values are requested, they are not wrapped in a tuple.
    """
    n_threads = _resolve_n_threads(n_threads)

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

    n = len(array)
    # Calculated from the shape, as the first stride of a contiguous array is arbitrary when the first dimension has length 1
    element_size = array.itemsize * math.prod(array.shape[1:])

    index = np.empty(n, dtype=np.int64)
    inverse = np.empty(n, dtype=np.int64) if return_inverse or return_groups else None
    counts = np.empty(n, dtype=np.int64) if return_counts or return_groups else None

    if n < _MIN_PARALLEL_SIZE or element_size in _SERIAL_ELEMENT_SIZES:
        n_threads = 1
    # Must stay alive during the call, as C only gets its address
    keys = _with_equal_nans(array)
    c = _c.unique(
        keys.ctypes.data,
        n,
        element_size,
        n_threads,
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
