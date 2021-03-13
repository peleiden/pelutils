from __future__ import annotations
import os
from dataclasses import dataclass

import numpy as np
import torch

from pelutils.tests import MainTest
from pelutils.datahandling import DataStorage

@dataclass
class T(DataStorage):
    a: np.ndarray
    b: torch.Tensor
    c: str
    d: dict[tuple[int], int]

class TestDatahandler(MainTest):
    def test_saveload(self):
        # Use dict data that is not json serializable
        datas = {"a": np.array([1]), "b": torch.Tensor([1]), "c": "lala", "d": {(1,2): 1}}
        t = T(**datas)
        t.save(self.test_dir)
        for f in ("a.npy", "b.pt", "data.json", "d.p"):
            print(f)
            assert os.path.isfile(os.path.join(self.test_dir, f))
        t = T.load(self.test_dir)
        for n, d in datas.items():
            assert getattr(t, n) == d
