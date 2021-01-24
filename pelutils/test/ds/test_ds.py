import numpy as np

from pelutils import set_seeds, throws
from pelutils.ds import unique

set_seeds(sum(ord(c) for c in "GME TO THE MOON! 🚀🚀🚀🚀🚀🚀🚀🚀"))


def test_unique():

    # Simple case: Ordered numbers from 0 to 99
    n = 100
    a = np.arange(n, dtype=np.uint32)
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

    # Multidimensional array
    a = np.random.randint(0, 10, (10, 5, 5))
    a[2] = a[4]
    a[3] = a[4]
    a[4] = a[6]
    u, index, inverse, counts = unique(a, return_index=True, return_inverse=True, return_counts=True)
    npu = np.unique(a, axis=0)
    assert len(u) == len(npu)
    assert u.shape == npu.shape
    assert np.all(a[index] == u)
    assert np.all(a == u[inverse])
    assert np.max(counts) == 2

    # Check error handling
    assert throws(ValueError, unique, np.array([]))

