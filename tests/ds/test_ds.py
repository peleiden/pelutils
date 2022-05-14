import numpy as np
import pytest

import torch
import torch.nn as nn

from pelutils import set_seeds
from pelutils.ds import unique, no_grad

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

def test_no_grad():
    # Simulate simple data with a batch size of three,
    # four data points per batch and five features
    def with_grad():
        x = torch.randn(3, 4, 5)
        y = torch.randn(3, 4, 1)
        simple_net = nn.Linear(5, 1)
        loss = (y - simple_net(x)).abs().sum()
        loss.backward()

    @no_grad
    def without_grad():
        with_grad()

    # This should work without problems
    with_grad()
    # This should fails, as gradients need to be tracked
    with pytest.raises(RuntimeError):
        without_grad()
