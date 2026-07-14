from pelutils.misc import except_keys


def test_except_keys():
    d = {"a": 3, "b": 5}
    d2 = except_keys(d, ["b", "c"])
    assert "a" in d and "b" in d
    assert "a" in d2 and "b" not in d2
