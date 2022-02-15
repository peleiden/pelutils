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
    """
    Decorator for running functions without pytorch tracking gradients, e.g.
    ```
    @no_grad
    def feed_forward(x):
        return net(x)
    ```
    """
    functools.wraps(fun)
    def wrapper(*args, **kwargs):
        with torch.no_grad():
            return fun(*args, **kwargs)
    return wrapper

class BatchFeedForward:
    """
    This class handles feedforwarding large batches that would otherwise cause memory overflow
    It works by splitting it into smaller batches, if it encounters a memory error
    Does not track gradients
    Notice that while this works for batches of varying sizes, this is not recommended usage, as it can be inefficient
    """

    def __init__(self, net: torch.nn.Module):
        self.net = net
        self.increase_factor = 2
        self.batches = 1

    @no_grad
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        while True:
            try:
                output_parts = [self.net(x[slice_]) for slice_ in self._get_slices(x)]
                output = torch.cat(output_parts)
                break
            # Usually caused by running out of vram. If not, the error is still raised, else batch size is reduced
            except RuntimeError as e:
                if "alloc" not in str(e):
                    raise e
                self._more_batches()
        return output

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward(x)

    def _more_batches(self):
        self.batches *= self.increase_factor

    def _get_slices(self, x: torch.Tensor) -> Generator:
        slice_size = len(x) // self.batches + 1
        # Final slice may have overflow, however this is simply ignored when indexing
        return (slice(i*slice_size, (i+1)*slice_size) for i in range(self.batches))
