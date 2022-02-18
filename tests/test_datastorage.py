from __future__ import annotations
import os
from dataclasses import dataclass

import numpy as np
import pytest
import rapidjson
import torch

from pelutils import UnitTestCollection, DataStorage


@dataclass
class T(DataStorage):
    a: np.ndarray
    b: torch.Tensor
    c: str
    d: dict[tuple[int], int]
    g = "not part of data"

@dataclass
class TCompatible(T):
    e: str = "loadable from T"

@dataclass
class TExtra(T, indent=4):
    e: np.ndarray
    f: float

class TMissingDecorator(DataStorage):
    a: int

class TestDatahandler(UnitTestCollection):

    data = {"a": np.array([1]), "b": torch.Tensor([1]), "c": "lala", "d": {(1,2): 1}}

    def test_saveload(self):
        # Use dict data that is not json serializable
        t = T(**self.data)
        t.save(self.test_dir)
        for f in ("a.npy", "b.pt", "data.json", "d.pkl"):
            assert os.path.isfile(os.path.join(self.test_dir, f))
        t = T.load(self.test_dir)
        for n, d in self.data.items():
            assert getattr(t, n) == d
        with open(os.path.join(self.test_dir, "data.json")) as f:
            assert "g" not in rapidjson.load(f)

    def test_compatible(self):
        t = T(**self.data)
        t.save(self.test_dir)
        t2 = TCompatible.load(self.test_dir)
        assert t2.e == "loadable from T"

    def test_missing_decorator(self):
        with pytest.raises(TypeError):
            TMissingDecorator(a=5)

    def test_indent(self):
        t = TExtra(**self.data, e=np.arange(5), f=5)
        t.save(self.test_dir)
        with open(os.path.join(self.test_dir, "data.json")) as f:
            lines = f.readlines()
        assert lines[1].startswith(4*" ")
