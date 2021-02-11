import pytest

from pelutils import Table

def test_table():
    t = Table()
    h = ["a", "69"]
    t.add_header(h)
    with pytest.raises(ValueError):
        t.add_row([1, 2, 3])
    t.add_row([12, 2], [True, False])
    assert str(t) == "\n".join([
        "a  | 69",
        "---+---",
        "12 |  2",
    ])

    t = Table()
    for i in range(3):
        t.add_row([i, str(i+1), i+2])
    assert "+" not in str(t)  # Check no header formatting

