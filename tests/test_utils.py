import pandas as pd
from numpy import array, ndarray

from pelutils._utils import isinstance_by_name


def test_isinstance_by_name():
    assert not isinstance_by_name(array([1, 2, 3]), "np", "ndarray")
    assert isinstance_by_name(array([1, 2, 3]), "numpy", "ndarray")
    assert isinstance_by_name(pd.DataFrame({"a": [1]}), "pandas", "DataFrame")
    assert isinstance_by_name(pd.Series([1]), "pandas", "Series")
    assert not isinstance_by_name(pd.Series([1]), "pd", "Series")
    assert not isinstance_by_name(ndarray, "np", "ndarray")
