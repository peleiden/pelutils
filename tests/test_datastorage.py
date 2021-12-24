from __future__ import annotations
import os
from dataclasses import dataclass

import numpy as np
import pytest
import torch

from pelutils import MainTest, DataStorage


@dataclass
class T(DataStorage):
    a: np.ndarray
    b: torch.Tensor
    c: str
    d: dict[tuple[int], int]

@dataclass
class TExtra(T):
    e: np.ndarray
    f: float

@dataclass
class TExtraIgnore(T):
    e: np.ndarray
    f: float
    ignore_missing = True

class TMissingDecorator(DataStorage):
    a: int

class TestDatahandler(MainTest):

    data = {"a": np.array([1]), "b": torch.Tensor([1]), "c": "lala", "d": {(1,2): 1}}

    def test_saveload(self):
        # Use dict data that is not json serializable
        t = T(**self.data)
        t.save(self.test_dir)
        print(os.listdir(self.test_dir))
        for f in ("a.npy", "b.pt", "data.json", "d.pkl"):
            assert os.path.isfile(os.path.join(self.test_dir, f))
        t = T.load(self.test_dir)
        for n, d in self.data.items():
            assert getattr(t, n) == d

    def test_ignore_missing(self):
        t = T(**self.data)
        t.save(self.test_dir)
        with pytest.raises(TypeError):
            TExtra.load(self.test_dir)
        t = TExtraIgnore.load(self.test_dir)
        assert t.e is None and t.f is None

    def test_missing_decorator(self):
        with pytest.raises(TypeError):
            TMissingDecorator(a=5)
