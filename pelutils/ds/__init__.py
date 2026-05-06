from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar, Union, cast

import numpy as np

from pelutils._utils import isinstance_by_name
from pelutils.types import AnyArray, BoolArray, FloatArray, IntArray

try:
    import torch

    _has_torch = True
except ModuleNotFoundError:
    _has_torch = False

import _pelutils_c as _c

import pelutils._c as _c_utils

ArrayOrTensor = Union["BoolArray | FloatArray | IntArray | torch.Tensor"]


def unique(  # noqa: PLR0912
    array: ...,
    *,
    return_index: bool = False,
    return_inverse: bool = False,
    return_counts: bool = False,
    axis: int = 0,
) -> ArrayOrTensor | tuple[ArrayOrTensor, ...]:
    """Similar to np.unique, but in linear time and returns unsorted. Also supports torch.Tensor and pandas Series."""
    is_tensor = False
    if _has_torch and isinstance(array, torch.Tensor):  # pyright: ignore[reportPossiblyUnboundVariable]
        is_tensor = True
        np_array = array.numpy()
    elif isinstance_by_name(array, "pandas", "Series"):
        np_array = array.values
    elif isinstance(array, np.ndarray):
        np_array = array
    else:
        raise TypeError(f"Unsupported array type {type(array)}, must be numpy array, torch tensor, or pandas dataframe.")

    np_array = cast(AnyArray, np_array)
    del array  # Prevent reuse - underlying tensor already referenced by np_array, which should be used from here

    if not np_array.size:
        raise ValueError("Array must be non-empty")

    if axis:
        axes = list(range(len(np_array.shape)))
        axes[0] = axis
        axes[axis] = 0
        np_array = np_array.transpose(axes)
    else:
        axes = None
    if not np_array.flags["C_CONTIGUOUS"]:
        np_array = np.ascontiguousarray(np_array)

    index = np.empty(len(np_array), dtype=np.int64)
    inverse = np.empty(len(np_array), dtype=np.int64) if return_inverse else None
    counts = np.empty(len(np_array), dtype=np.int64) if return_counts else None

    c = _c.unique(
        *_c_utils.get_array_c_args(np_array),
        index.ctypes.data,
        inverse.ctypes.data if inverse is not None else 0,
        counts.ctypes.data if counts is not None else 0,
    )

    index = index[:c]
    if axis:
        np_array = np_array[index]
        np_array = np.ascontiguousarray(np_array.transpose(axes))
    else:
        np_array = np_array[index]
    ret = [np_array]
    if return_index:
        ret.append(index)
    if return_inverse:
        assert inverse is not None
        ret.append(inverse)
    if return_counts:
        assert counts is not None
        ret.append(counts[index])

    if _has_torch and is_tensor:
        ret = [torch.from_numpy(x) for x in ret]  # pyright: ignore[reportPossiblyUnboundVariable]

    return tuple(ret) if len(ret) > 1 else ret[0]


def tensor_bytes(x: AnyArray | torch.Tensor) -> int:
    """Calculate the size of a numpy array or torch tensor in bytes."""
    if isinstance(x, np.ndarray):
        return x.nbytes
    elif _has_torch and isinstance(x, torch.Tensor):  # pyright: ignore[reportUnnecessaryIsInstance, reportPossiblyUnboundVariable]
        return x.element_size() * x.numel()
    else:
        raise TypeError(f"Unable to calculate the number of bytes of a tensor with type {type(x)}")
