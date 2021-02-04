from __future__ import annotations
import os
import ctypes
import functools
import platform
from typing import Callable, Iterable, Type

import numpy as np

# Path to directory where package files are located
_base_path = os.path.abspath(os.path.dirname(__file__))

_import_error = ModuleNotFoundError("To use the ds submodule, you must install pelutils[ds]")

try:
    import torch
except ModuleNotFoundError as e:
    raise _import_error from e

from pelutils import c_ptr


_so_error = NotImplementedError("unique function is currently only supported on x86_64 Linux")
if all(substr in platform.platform().lower() for substr in ("linux", "x86_64")):
    _lib = ctypes.cdll.LoadLibrary(f"{_base_path}/ds.so")
def unique(array: np.ndarray, *, return_index=False, return_inverse=False, return_counts=False)\
    -> np.ndarray | Iterable[np.ndarray]:
    """
    Similar to np.unique with axis=0, but in linear time and unsorted
    Currently only works properly on x86_64 Linux
    On other platforms, it wraps np.unique, which returns a sorted array but otherwise has same output
    """
    if "_lib" not in globals():
        raise _so_error
    if not array.flags["C_CONTIGUOUS"]:
        raise ValueError("Array must be contiguous row-major")
    if not array.size:
        raise ValueError("Array must be non-empty")
    index   = np.empty(len(array), dtype=int)
    inverse = np.empty(len(array), dtype=int) if return_inverse else None
    counts  = np.empty(len(array), dtype=int) if return_counts  else None

    # Calculate number of bytes between each row
    stride = array.dtype.itemsize
    if len(array.shape) > 1:
        stride *= int(np.prod(array.shape[1:]))
    c = _lib.unique(len(array), stride, c_ptr(array), c_ptr(index), c_ptr(inverse), c_ptr(counts))

    index = index[:c]
    ret = [array[index]]
    if return_index:
        ret.append(index)
    if return_inverse:
        ret.append(inverse)
    if return_counts:
        # pylint: disable=unsubscriptable-object
        ret.append(counts[index])
    return tuple(ret) if len(ret) > 1 else ret[0]

def reset_cuda():
    """ Clear cache and synchronize cuda """
    torch.cuda.empty_cache()
    if torch.cuda.is_available():
        torch.cuda.synchronize()

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
    Only works when gradient should not be tracked
    """

    def __init__(self, net: Type[torch.nn.Module], data_points: int, increase_factor=2):
        """
        net: torch network
        data_points: Number of data points in each feed forward
        increase_factor: Multiply number of batches with this each time a memory error occurs
        """
        self.net = net
        self.data_points = data_points
        self.increase_factor = increase_factor
        self.batches = 1

    @no_grad
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        while True:
            try:
                output_parts = [self.net(x[slice_]) for slice_ in self._get_slices()]
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

    def update_net(self, net: Type[torch.nn.Module]):
        self.net = net

    def _more_batches(self):
        self.batches *= self.increase_factor

    def _get_slices(self):
        slice_size = self.data_points // self.batches + 1
        # Final slice may have overflow, however this is simply ignored when indexing
        slices = [slice(i*slice_size, (i+1)*slice_size) for i in range(self.batches)]
        return slices
