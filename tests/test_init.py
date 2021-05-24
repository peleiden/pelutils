import os
from pelutils import EnvVars, split_path
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
