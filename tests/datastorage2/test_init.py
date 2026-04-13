from datetime import date

import numpy as np
import pandas as pd
import pytest
import torch

from pelutils.datastorage2 import DataStorage2
from pelutils.datastorage2._pretty_json import _PICKLE_PREFIX
from pelutils.tests import UnitTestCollection
from pelutils.types import FloatArray


class DeepCollection(DataStorage2):
    np_arr: FloatArray
    tensor: torch.Tensor
    df: pd.DataFrame


class Collection(DataStorage2):
    string: str
    list_of_floats: list[float]
    tuple_of_floats: tuple[float, ...]
    tuple_of_ints: tuple[int, ...]
    collection: DeepCollection


class WhackStorage(DataStorage2):
    """Whack struct with lots of nested non-native data types."""

    date: date
    np_arr: FloatArray
    tensor: torch.Tensor
    df: pd.DataFrame
    collection: Collection


data = WhackStorage(
    date=date(2026, 1, 1),
    np_arr=np.arange(5, dtype=np.float16),
    tensor=torch.ones(5),
    df=pd.DataFrame({"col1": [1, 2, 3], "col": np.arange(3)}),
    collection=Collection(
        string="Hello There",
        list_of_floats=[1.0, 2.0, 3.0],
        tuple_of_floats=(0.1, 0.2, 0.3),
        tuple_of_ints=tuple(range(500)),
        collection=DeepCollection(
            np_arr=np.arange(10),
            tensor=torch.zeros(0, dtype=bool),
            df=pd.DataFrame({"col1": ["1", "2", "3"], "col": np.arange(3)}),
        ),
    ),
)


class TestDataStorage2(UnitTestCollection):
    def test_save_load(self):
        # Test save and load with custom file name
        save_path = data.save(self.test_dir, filename="bollocks")
        assert '"date": "2026-01-01"' in save_path.read_text()  # Ensure that dates get serialised to strings
        WhackStorage.load(self.test_dir, filename="bollocks")
        # Set save and load with default file name
        data.save(self.test_dir)
        loaded = WhackStorage.load(self.test_dir)
        assert data.date == loaded.date
        assert (data.np_arr == loaded.np_arr).all()
        assert data.np_arr.dtype == loaded.np_arr.dtype
        assert (data.tensor == loaded.tensor).all()
        assert data.tensor.dtype is loaded.tensor.dtype
        assert data.df.equals(loaded.df)
        assert data.collection.string == loaded.collection.string
        assert data.collection.list_of_floats == data.collection.list_of_floats
        assert data.collection.tuple_of_floats == data.collection.tuple_of_floats
        assert data.collection.tuple_of_ints == data.collection.tuple_of_ints
        assert (data.collection.collection.np_arr == loaded.collection.collection.np_arr).all()
        assert data.collection.collection.np_arr.dtype == loaded.collection.collection.np_arr.dtype
        assert (data.collection.collection.tensor == loaded.collection.collection.tensor).all()
        assert data.collection.collection.tensor.dtype is loaded.collection.collection.tensor.dtype
        assert data.collection.collection.df.equals(loaded.collection.collection.df)

        # Check that corrupted data raises a ValueError
        json_content = data._resolve_save_file(self.test_dir).read_text()
        json_content = json_content.replace(_PICKLE_PREFIX, f"_{_PICKLE_PREFIX}")
        data._resolve_save_file(self.test_dir).write_text(json_content)
        with pytest.raises(ValueError):
            WhackStorage.load(self.test_dir)
