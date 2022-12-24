import ctypes

import numpy as np
import pytest
import torch

import pelutils._c as c_utils
from pelutils import OS


@pytest.mark.skipif(OS.is_windows, reason="This test does spooky shit that scares Windows")
def test_get_c_array_args():

    for dtype in int, float, np.float16, np.int32:
        shape = (2, 4, 3)
        np_arr = np.empty(shape, dtype=dtype)
        arr_p, ndim, dims_p, strides_p = c_utils.get_array_c_args(torch.from_numpy(np_arr))
        assert arr_p == np_arr.ctypes.data
        assert ndim == len(shape)

        itemsize = np.dtype(np.uint).itemsize
        s = np_arr.dtype.itemsize
        for i, d in enumerate(shape[::-1]):
            i = len(shape) - i - 1
            assert d == ctypes.c_uint64.from_address(dims_p+i*itemsize).value
            assert s == ctypes.c_uint64.from_address(strides_p+i*itemsize).value
            s *= d
