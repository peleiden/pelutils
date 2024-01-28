import numpy as np
import pytest

import torch

from pelutils import set_seeds
from pelutils.ds import unique, tensor_bytes

set_seeds(sum(ord(c) for c in "GME TO THE MOON! 🚀🚀🚀🚀🚀🚀🚀🚀"))


def test_unique():

    # Simple case: Ordered numbers from 0 to 99
    n = 100
    a = np.arange(n, dtype=np.uint32)
    u = unique(a)
    assert np.all(a == u)
    u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True)
    assert np.all(a == u)
    assert np.all(a == index)
    assert np.all(a == inverse)
    assert np.all(counts == 1)

    # Slightly more complex case with some non-unique values
    a[2:4] = 50
    a[[5, 16, 3]] = 69
    a = a.astype(np.float16)
    u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True)
    argsort = np.argsort(u)
    npu, npindex, npcounts = np.unique(a, return_index=True, return_counts=True)
    assert np.all(u[argsort] == npu)
    assert np.all(index[argsort] == npindex)
    assert np.all(a == u[inverse])
    assert np.all(counts[argsort] == npcounts)

    # Axis and multidimensional array
    a = np.random.randint(0, 5, (10, 5, 5))
    a[2] = a[4]
    a[3] = a[4]
    a[4] = a[6]
    for axis in range(len(a.shape)):
        u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True, axis=axis)
        npu, npcounts = np.unique(a, return_counts=True, axis=axis)
        assert u.shape == npu.shape
        assert np.all(a[(*[slice(None)]*axis, index)] == u)
        assert np.all(a == u[(*[slice(None)]*axis, inverse)])
        assert np.all(np.sort(counts) == np.sort(npcounts))

    # Check error handling
    with pytest.raises(ValueError):
        unique(np.array([]))

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
        np_size = tensor_bytes(np_array)
        torch_size = tensor_bytes(torch_tensor)
        assert isinstance(np_size, int)
        assert isinstance(torch_size, int)
        assert np_size == torch_size
        size = np_size

        if shape[0] > 1 and size > 0:
            # Test views
            assert tensor_bytes(np_array[::2]) < size
            assert tensor_bytes(torch_tensor[::2]) < size
            assert tensor_bytes(np_array[::2]) == tensor_bytes(torch.from_numpy(np_array[::2]))
            assert tensor_bytes(torch_tensor[::2]) == tensor_bytes(torch_tensor[::2].numpy())

    with pytest.raises(TypeError):
        tensor_bytes([1, 2, 3])

def test_tensor_size():
    sizes = np.arange(5)
    for x in sizes:
        _test_tensor_size([x])
        for y in sizes:
            _test_tensor_size([x, y])
            for z in sizes:
                _test_tensor_size([x, y, z])
