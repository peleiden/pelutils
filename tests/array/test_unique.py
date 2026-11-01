import importlib

import numpy as np
import pytest
import torch

from pelutils.array import unique

_unique_module = importlib.import_module("pelutils.array._unique")

seed = sum(ord(c) for c in "GME TO THE MOON! 🚀🚀🚀🚀🚀🚀🚀🚀")
np_rng = np.random.default_rng(seed)


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
    assert a_t.numpy().dtype == u_t.dtype
    assert isinstance(u_t, np.ndarray)
    assert isinstance(index_t, np.ndarray)
    assert isinstance(inverse_t, np.ndarray)
    assert isinstance(counts_t, np.ndarray)
    assert np.all(a == a_t.numpy())
    assert np.all(u == u_t)
    assert np.all(index == index_t)
    assert np.all(inverse == inverse_t)
    assert np.all(counts == counts_t)

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
    a = np_rng.integers(0, 5, (10, 5, 5))
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

    # Check error handling
    with pytest.raises(TypeError):
        unique(np.array([str, "", 1, 2, object, object()]))
    with pytest.raises(TypeError):
        unique(np.array(str))
    with pytest.raises(ValueError):
        unique(torch.tensor(5))


def _all_results(a, **kwargs):
    return unique(a, return_index=True, return_inverse=True, return_counts=True, return_groups=True, **kwargs)


@pytest.mark.parametrize(
    ("array", "expected_values"),
    [
        (np.arange(1)[::-1], np.array([0])),  # Negative stride with a single element
        (np.arange(10)[9:][::5], np.array([9])),  # Large stride with a single element at the end of the buffer
    ],
)
def test_unique_arbitrary_first_stride(array, expected_values):
    assert array.flags["C_CONTIGUOUS"]
    assert (unique(array) == expected_values).all()


def test_unique_zero_size_elements_parallel():
    a = np.empty((2**18 + 100, 0), dtype=int)
    values, counts = unique(a, return_counts=True, n_threads=2)
    assert values.shape == (1, 0)
    assert counts.tolist() == [len(a)]


def test_unique_padding_bytes_are_compared():
    dtype = np.dtype({"names": ["a", "b"], "formats": ["i1", "i8"], "offsets": [0, 8], "itemsize": 16})
    buffer = np.zeros(2 * dtype.itemsize, dtype=np.uint8)
    buffer[1] = 1  # A padding byte in the first element only
    a = np.frombuffer(buffer, dtype=dtype)
    assert a[0] == a[1]
    assert len(unique(a)) == 2


@pytest.mark.skipif(
    np.finfo(np.longdouble).nmant != 63 or np.dtype(np.longdouble).itemsize <= 10,
    reason="Only 80-bit extended precision stored with padding has unused bytes",
)
def test_unique_longdouble_padding_bytes_are_compared():
    element = bytearray(np.array([1], dtype=np.longdouble).tobytes())
    element[10:] = bytes(len(element) - 10)
    other = bytearray(element)
    other[-1] = 1
    a = np.frombuffer(bytes(element + other), dtype=np.longdouble)
    assert a[0] == a[1]
    assert len(unique(a)) == 2


def test_unique_rejects_objects():
    with pytest.raises(TypeError):
        unique(np.array([(1, "a")], dtype=[("i", "i4"), ("o", "O")]))


@pytest.mark.parametrize("n_threads", [2.5, "2"])
@pytest.mark.parametrize("n", [1, 2**18 + 100])
def test_unique_rejects_non_integer_n_threads(n, n_threads):
    with pytest.raises(TypeError):
        unique(np.arange(n), n_threads=n_threads)


def test_unique_accepts_numpy_integer_n_threads():
    assert unique(np.arange(3), n_threads=np.int64(2)).tolist() == [0, 1, 2]


def test_unique_failed_allocation():
    # Far beyond what can be allocated, so allocating the work for all threads fails before any thread starts
    with pytest.raises(MemoryError):
        unique(np.arange(2**18 + 100), n_threads=2**48)
    # The result is unaffected afterwards
    assert len(unique(np.arange(2**18 + 100), n_threads=2)) == 2**18 + 100


@pytest.mark.parametrize("array", [np.empty((5, 0), dtype=int), np.empty(5, dtype=[])])
def test_unique_zero_size_elements(array):
    values, index, inverse, counts, groups = _all_results(array)
    assert values.shape == (1, *array.shape[1:])
    assert index.tolist() == [0]
    assert inverse.tolist() == [0] * 5
    assert counts.tolist() == [5]
    assert groups[0].tolist() == list(range(5))


@pytest.mark.parametrize("n", [100, 2**14, 2**16])
@pytest.mark.parametrize("dtype", [np.uint8, np.int16, np.int32, np.int64, "S3", "U5", "f8,i1", "c16"])
def test_unique_element_sizes(n, dtype):
    # Includes table growth and both code paths for 2-byte elements
    a = np_rng.integers(0, n // 2, n).astype(np.int64)
    if dtype == "f8,i1":
        a = np.array([(x, x % 7) for x in a.tolist()], dtype=dtype)
    else:
        a = (a % 100 if dtype == "S3" else a).astype(dtype)
    values, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True)
    assert (values == a[index]).all()
    assert (values[inverse] == a).all()
    assert counts.sum() == n
    assert (np.diff(index) > 0).all()
    assert len(values) == len(np.unique(a))


def test_unique_unaligned():
    dtype = np.dtype([("a", np.int8), ("b", np.int64)], align=False)
    a = np.zeros(20, dtype=dtype)
    a["b"] = np.arange(20) % 3
    assert a.dtype.itemsize == 9
    assert len(unique(a)) == 3
    buffer = np.zeros(161, dtype=np.uint8)
    b = np.frombuffer(buffer, dtype=np.int64, count=20, offset=1)
    assert not b.flags["ALIGNED"]
    assert unique(b).tolist() == [0]


def test_unique_first_occurrence_order():
    values, index = unique([3, 1, 3, 2, 1], return_index=True)
    assert values.tolist() == [3, 1, 2]
    assert index.tolist() == [0, 1, 3]


def _nans(dtype, bit_patterns):
    uint_dtype = f"u{np.dtype(dtype).itemsize}"
    return np.array(bit_patterns, dtype=uint_dtype).view(dtype)


@pytest.mark.parametrize(
    ("dtype", "bit_patterns"),
    [
        (np.float16, [0x7E00, 0xFE00, 0x7E01]),
        (np.float32, [0x7FC00000, 0xFFC00000, 0x7FC00001]),
        (np.float64, [0x7FF8000000000000, 0xFFF8000000000000, 0x7FF8000000000001]),
    ],
)
def test_unique_equal_nans(dtype, bit_patterns):
    nans = _nans(dtype, bit_patterns)
    a = np.concatenate([np.array([1, 0, -0.0], dtype=dtype), nans, np.array([1], dtype=dtype)])
    original_bytes = a.tobytes()
    values, index, inverse, counts, groups = _all_results(a)
    assert a.tobytes() == original_bytes
    assert values.tobytes() == a[[0, 1, 2, 3]].tobytes()  # NaN keeps its first bits and -0.0 stays distinct
    assert index.tolist() == [0, 1, 2, 3]
    assert inverse.tolist() == [0, 1, 2, 3, 3, 3, 0]
    assert counts.tolist() == [2, 1, 1, 3]
    assert groups[3].tolist() == [3, 4, 5]


def test_unique_equal_nans_complex_and_axis():
    a = np.array([complex(np.nan, 1), complex(1, np.nan), complex(np.nan, np.nan), 1])
    assert len(unique(a)) == 2

    nan1, nan2 = _nans(np.float64, [0x7FF8000000000000, 0x7FF8000000000001])
    rows = np.array([[1, nan1], [1, nan2], [2, nan1]])
    assert len(unique(rows)) == 2
    assert unique(rows, return_inverse=True)[1].tolist() == [0, 0, 1]
    assert unique(rows.T, return_inverse=True, axis=1)[1].tolist() == [0, 0, 1]


@pytest.mark.parametrize("n_threads", [1, 3])
def test_unique_equal_nans_large(n_threads):
    a = np_rng.integers(0, 10, 2**18 + 100).astype(np.float64)
    bits = a.view(np.uint64)
    is_nan = np_rng.random(len(a)) < 0.1
    bits[is_nan] = 0x7FF8000000000000 | np_rng.integers(0, 2**51, is_nan.sum(), dtype=np.uint64)
    values, index = unique(a, return_index=True, n_threads=n_threads)
    assert len(values) == 11
    assert values.tobytes() == a[index].tobytes()


@pytest.mark.parametrize(
    "array",
    [
        np.array(["", "a", "", "abc", "a", "🚀", "abc\0", "a b"]),
        np.array([b"", b"a", b"", b"abc", b"a", b"\xff"]),
        np.array(["a", "b", "a"]),
        np.array([b"a", b"b", b"a"]),
        np.array([True, False, True]),
        np.array(["2020-01-01", "NaT", "2020-01-02", "NaT", "2020-01-01"], dtype="datetime64[D]"),
        np.array([1, 2, 1], dtype="timedelta64[s]"),
        np.array([b"ab", b"cd", b"ab"], dtype="V2"),
        np.array([("a", 1), ("b", 1), ("a", 1), ("a", 2)], dtype=[("s", "U2"), ("i", "i4")]),
    ],
)
@pytest.mark.parametrize("repeats", [1, 2**18 // 3 + 1])
def test_unique_non_numeric(array, repeats):
    a = np.tile(array, repeats)
    expected = {}
    for i, x in enumerate(a.tolist()[: len(array)]):
        expected.setdefault(str(x), i)
    for n_threads in 1, 4:
        values, index, inverse = unique(a, return_index=True, return_inverse=True, n_threads=n_threads)
        assert values.dtype == a.dtype
        assert index.tolist() == list(expected.values())
        assert values.tobytes() == a[index].tobytes()
        assert a.tobytes() == values[inverse].tobytes()


@pytest.mark.parametrize("n_unique", [1, 100, 2**18 + 100])
@pytest.mark.parametrize("dtype", [np.int32, np.int64, "U3", "S11"])
@pytest.mark.parametrize("n_threads", [2, 7])
def test_unique_parallel_matches_serial(n_unique, dtype, n_threads):
    n = 2**18 + 100
    a = (np_rng.permutation(n) % n_unique).astype(dtype)
    serial = _all_results(a, n_threads=1)
    parallel = _all_results(a, n_threads=n_threads)
    for serial_result, parallel_result in zip(serial[:-1], parallel[:-1], strict=True):
        assert np.array_equal(serial_result, parallel_result)
    assert len(serial[-1]) == len(parallel[-1])
    assert all(np.array_equal(g1, g2) for g1, g2 in zip(serial[-1], parallel[-1], strict=True))
    # Each return value on its own, since the parallel code allocates buffers depending on these
    assert np.array_equal(serial[0], unique(a, n_threads=n_threads))
    assert np.array_equal(serial[3], unique(a, return_counts=True, n_threads=n_threads)[1])


def test_unique_parallel_axis():
    a = np_rng.integers(0, 2, (2**18 + 100, 20))
    b = a.T
    for array, axis in (a, 0), (b, 1), (b, -1):
        serial = unique(array, return_inverse=True, axis=axis, n_threads=1)
        parallel = unique(array, return_inverse=True, axis=axis, n_threads=3)
        assert np.array_equal(serial[0], parallel[0])
        assert np.array_equal(serial[1], parallel[1])


def test_resolve_n_threads(monkeypatch):
    monkeypatch.setattr(_unique_module, "_available_cpus", lambda: 12)
    assert _unique_module._resolve_n_threads(None) == 8
    assert _unique_module._resolve_n_threads(32) == 32
    monkeypatch.setattr(_unique_module, "_available_cpus", lambda: 3)
    assert _unique_module._resolve_n_threads(None) == 3
    with pytest.raises(ValueError):
        unique([1], n_threads=0)


def test_unique_groups():
    values, groups = unique([1, 2, 3, 1], return_groups=True)
    assert values.tolist() == [1, 2, 3]
    assert [group.tolist() for group in groups] == [[0, 3], [1], [2]]

    values, groups = unique(np.array([]), return_groups=True)
    assert len(values) == 0
    assert groups == []

    _, groups = unique([5], return_groups=True)
    assert [group.tolist() for group in groups] == [[0]]

    a = np_rng.integers(0, 3, (2, 200))
    values, index, inverse, counts, groups = _all_results(a, axis=1)
    assert len(groups) == values.shape[1]
    for k, group in enumerate(groups):
        assert group.dtype == np.int64
        assert np.array_equal(group, np.flatnonzero(inverse == k))
        assert group[0] == index[k]
        assert len(group) == counts[k]
