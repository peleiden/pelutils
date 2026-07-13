import numpy as np
import pandas as pd
import pytest
import torch

from pelutils.ds import tensor_bytes, unique

_seed = sum(ord(c) for c in "GME TO THE MOON! 🚀🚀🚀🚀🚀🚀🚀🚀")
np.random.seed(_seed)  # noqa: NPY002
torch.manual_seed(_seed)


def test_unique():  # noqa: PLR0915
    # Simple case: Ordered numbers from 0 to 99
    n = 100
    a = np.arange(n, dtype=np.uint32)
    u = unique(a)
    assert np.all(a == u)
    u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True)
    assert a.dtype == u.dtype
    assert isinstance(u, np.ndarray)
    assert isinstance(index, np.ndarray)
    assert isinstance(inverse, np.ndarray)
    assert isinstance(counts, np.ndarray)
    assert np.all(a == u)
    assert np.all(a == index)
    assert np.all(a == inverse)
    assert np.all(counts == 1)

    # Test torch support
    a_t = torch.from_numpy(a)
    u_t, index_t, inverse_t, counts_t = unique(a_t, return_index=True, return_inverse=True, return_counts=True)
    assert a_t.dtype == u_t.dtype
    assert isinstance(u_t, torch.Tensor)
    assert isinstance(index_t, torch.Tensor)
    assert isinstance(inverse_t, torch.Tensor)
    assert isinstance(counts_t, torch.Tensor)
    assert np.all(a == a_t.numpy())
    assert np.all(u == u_t.numpy())
    assert np.all(index == index_t.numpy())
    assert np.all(inverse == inverse_t.numpy())
    assert np.all(counts == counts_t.numpy())

    # Slightly more complex case with some non-unique values
    a[2:4] = 50
    a[[5, 16, 3]] = 69
    a = a.astype(np.float16)
    u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True)
    assert a.dtype == u.dtype
    argsort = np.argsort(u)
    npu, npindex, npcounts = np.unique(a, return_index=True, return_counts=True)
    assert np.all(u[argsort] == npu)
    assert np.all(index[argsort] == npindex)
    assert np.all(a == u[inverse])
    assert np.all(counts[argsort] == npcounts)

    # Axis and multidimensional array
    a = np.random.randint(0, 5, (10, 5, 5))  # noqa: NPY002
    a[2] = a[4]
    a[3] = a[4]
    a[4] = a[6]
    for axis in range(len(a.shape)):
        u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True, axis=axis)
        npu, npcounts = np.unique(a, return_counts=True, axis=axis)
        assert u.shape == npu.shape
        assert np.all(a[(*[slice(None)] * axis, index)] == u)
        assert np.all(a == u[(*[slice(None)] * axis, inverse)])
        assert np.all(np.sort(counts) == np.sort(npcounts))

    int_array = np.array([1, 2, 3, 1, 0, 2, 3, 1, 2, 101, 10, 10, 101, 101, 1, 1, 3, 2, 1])
    bytes_array = np.array([x.item().to_bytes(x, "big") for x in int_array])
    str_array = np.array([str(x) for x in int_array])
    iu, iidx, iinv, ic = unique(int_array, return_index=True, return_inverse=True, return_counts=True)
    bu, bidx, binv, bc = unique(bytes_array, return_index=True, return_inverse=True, return_counts=True)
    su, sidx, sinv, sc = unique(str_array, return_index=True, return_inverse=True, return_counts=True)
    assert len(iu) == len(bu) == len(su)
    assert (iu == np.array([int(x) for x in su])).all()
    assert (iu == np.array([int.from_bytes(b, "big") for b in bu])).all()
    assert (iidx == bidx).all() and (iidx == sidx).all()
    assert (iinv == binv).all() and (iinv == sinv).all()
    assert (ic == bc).all() and (ic == sc).all()

    u, index, inverse, counts = unique(np.array([]), return_index=True, return_inverse=True, return_counts=True)
    assert u.dtype == np.array([]).dtype
    assert len(u) == len(index) == len(inverse) == len(counts) == 0

    data_frame = pd.DataFrame({"a": np.array([1, 2, 3, 1], dtype=np.float16)})
    with pytest.raises(TypeError):
        unique(data_frame)
    u, c = unique(data_frame.a, return_counts=True)
    assert data_frame.a.dtype == u.dtype
    assert len(u) == 3
    assert c.sum() == len(data_frame)

    # Check error handling
    with pytest.raises(TypeError):
        unique(np.array([str, "", 1, 2, object, object()]))
    with pytest.raises(TypeError):
        unique(np.array(str))
    with pytest.raises(ValueError):
        unique(torch.tensor(5))


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
