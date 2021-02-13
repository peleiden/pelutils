from pelutils.logger import log


def test_bool_input():
    # Default to True
    assert log.bool_input("")
    assert log.bool_input("Yes")
    assert not log.bool_input("No")

    # Default to False
    assert not log.bool_input("", False)
    assert log.bool_input("Yes", False)
    assert not log.bool_input("No", False)
