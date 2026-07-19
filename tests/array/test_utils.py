import ctypes

import numpy as np
import pytest
import torch

from pelutils.array import array_bytes, array_ptr


def _test_tensor_size(shape: list[int]):
    dtypes = (
        (np.uint8, torch.uint8),
        (np.int16, torch.int16),
        (np.int32, torch.int32),
        (np.int64, torch.int64),
        (np.float16, torch.float16),
        (np.float32, torch.float32),
        (np.float64, torch.float64),
    )
    for np_dtype, torch_dtype in dtypes:
        np_array = np.empty(shape, dtype=np_dtype)
        torch_tensor = torch.empty(shape, dtype=torch_dtype)
        assert len(np_array.shape) == len(torch_tensor.shape)
        np_size = array_bytes(np_array)
        torch_size = array_bytes(torch_tensor)
        assert isinstance(np_size, int)
        assert isinstance(torch_size, int)
        assert np_size == torch_size
        size = np_size

        if shape[0] > 1 and size > 0:
            # Test views
            assert array_bytes(np_array[::2]) < size
            assert array_bytes(torch_tensor[::2]) < size
            assert array_bytes(np_array[::2]) == array_bytes(torch.from_numpy(np_array[::2]))
            assert array_bytes(torch_tensor[::2]) == array_bytes(torch_tensor[::2].numpy())


def test_array_ptr():
    with pytest.raises(TypeError):
        array_ptr(None)
    with pytest.raises(ValueError):
        array_ptr(np.arange(5)[::2])
    assert isinstance(array_ptr(torch.arange(5)), ctypes.c_void_p)
    a = torch.arange(5)
    assert array_ptr(a).value == array_ptr(a.numpy()).value


def test_tensor_size():
    sizes = np.arange(5)
    for x in sizes:
        _test_tensor_size([x])
        for y in sizes:
            _test_tensor_size([x, y])
            for z in sizes:
                _test_tensor_size([x, y, z])
