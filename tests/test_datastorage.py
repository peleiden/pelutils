from __future__ import annotations
from dataclasses import dataclass
import os

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
class TExtra(T):
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
        assert os.path.isfile(os.path.join(self.test_dir, T.json_name()))
        assert os.path.isfile(os.path.join(self.test_dir, T.pickle_name()))
        t = T.load(self.test_dir)
        for n, d in self.data.items():
            assert getattr(t, n) == d
        with open(os.path.join(self.test_dir, T.json_name())) as f:
            assert "g" not in rapidjson.load(f)

    def test_compatible(self):
        t = T(**self.data)
        t.save(self.test_dir)
        t2 = TCompatible.load(self.test_dir, T.__name__)
        assert t2.e == "loadable from T"

    def test_missing_decorator(self):
        with pytest.raises(TypeError):
            TMissingDecorator(a=5)

    def test_indent(self):
        t = TExtra(**self.data, e=np.arange(5), f=5)
        t.save(self.test_dir, indent=7)
        with open(os.path.join(self.test_dir, TExtra.json_name())) as f:
            lines = f.readlines()
        assert lines[1].startswith(7 * " ")

    def test_custom_save_name(self):
        t = T(**self.data)
        t.save(self.test_dir, "custom")
        assert os.path.isfile(os.path.join(self.test_dir, T.json_name("custom")))
        assert os.path.isfile(os.path.join(self.test_dir, T.pickle_name("custom")))
        with pytest.raises(FileNotFoundError):
            T.load(self.test_dir, "customm")
        T.load(self.test_dir, "custom")
