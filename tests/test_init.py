import os

import numpy as np

from pelutils import EnvVars, split_path, binary_search
from pelutils.tests import MainTest


class TestInit(MainTest):

    def test_envvars(self):
        os.environ["var1"] = "v1"
        assert os.environ["var1"] == "v1"
        assert "var2" not in os.environ
        with EnvVars(var1="v2", var2=2):
            assert os.environ["var1"] == "v2"
            assert os.environ["var2"] == "2"
        assert os.environ["var1"] == "v1"
        assert "var2" not in os.environ

    def test_split_path(self):
        empty = ""
        assert split_path(empty) == ["."]
        root = "/"
        assert split_path(root) == ["", ""]
        absolute = "/home/senate"
        assert split_path(absolute) == ["", "home", "senate"]
        assert split_path(absolute + "/") == ["", "home", "senate"]
        relative = "use/pelutils/pls.py"
        assert split_path(relative) == ["use", "pelutils", "pls.py"]

    def test_binary_search(self):
        data = np.random.randint(0, 100, 100)
        data = np.sort(data)
        for elem in data:
            assert binary_search(elem, data) is not None
            assert data[binary_search(elem, data)] == elem
        assert binary_search(-1, data) is None
        assert binary_search(100, data) is None
