from pelutils import split_path


def test_split_path():
    empty = ""
    assert split_path(empty) == ["."]
    root = "/"
    assert split_path(root) == ["", ""]
    absolute = "/home/senate"
    assert split_path(absolute) == ["", "home", "senate"]
    assert split_path(absolute + "/") == ["", "home", "senate"]
    relative = "use/pelutils/pls.py"
    assert split_path(relative) == ["use", "pelutils", "pls.py"]
