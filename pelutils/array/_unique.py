from __future__ import annotations

from typing import TypeVar, cast

import _pelutils_c as _c
import numpy as np
import numpy.typing as npt

import pelutils._c as c_utils
from pelutils.misc._conditional_import import import_pandas, import_torch
from pelutils.types import AnyArray

pd = import_pandas()
torch = import_torch()

_ArrayT = TypeVar("_ArrayT", bound=npt.ArrayLike)


def unique(  # noqa: PLR0912
    array: _ArrayT,
    *,
    return_index: bool = False,
    return_inverse: bool = False,
    return_counts: bool = False,
    axis: int = 0,
) -> _ArrayT | tuple[_ArrayT, ...]:
    """Return unique elements in a given numpy array (or torch tensor or pandas series).

    This function works very similar to np.unique, but it runs in linear time, making it significantly faster
    for large arrays. The returned unique elements are unsorted, however.
    """
    is_tensor = False
    if torch is not None and isinstance(array, torch.Tensor):
        is_tensor = True
        np_array = array.numpy()
    elif pd is not None and isinstance(array, pd.Series):
        np_array = array.values
    elif isinstance(array, np.ndarray):
        if np.issubdtype(array.dtype, np.object_):
            raise TypeError(f"Unsupported array dtype {array.dtype}")
        np_array = array
    else:
        raise TypeError(f"Unsupported array type {type(array)}, must be numpy array, torch tensor, or pandas dataframe.")

    if np_array.ndim == 0:
        raise ValueError("unique does not work for shape-less arrays")

    np_array = cast(AnyArray, np_array)
    del array  # Prevent reuse - underlying tensor already referenced by np_array, which should be used from here

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
        *c_utils.get_array_c_args(np_array),
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

    if torch is not None and is_tensor:
        ret = [torch.from_numpy(x) for x in ret]

    return tuple(ret) if len(ret) > 1 else ret[0]  # pyright: ignore[reportReturnType]
