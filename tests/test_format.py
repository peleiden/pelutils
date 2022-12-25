from string import ascii_letters
import os

from pelutils import Table
import pytest


def test_table():
    t = Table()
    h = ["a", "69"]
    t.add_header(h)
    with pytest.raises(ValueError):
        t.add_row([1, 2, 3])
    t.add_row([12, 2], [True, False])
    assert str(t) == os.linesep.join([
        "a  | 69",
        "---+---",
        "12 |  2",
    ])

    t = Table()
    for i in range(3):
        t.add_row([i, str(i+1), i+2])
    assert "+" not in str(t)  # Check no header formatting

def test_tex():
    t = Table()
    t.add_header(list(ascii_letters))
    for i in range(3):
        t.add_row([i * x for x in range(len(ascii_letters))])
    tex = t.tex()
    texlines = tex.splitlines()
    assert r"\toprule" in texlines[0]
    assert r"\midrule" in texlines[2]
    assert r"\bottomrule" in texlines[-1]

    for letter in ascii_letters:
        assert letter in texlines[1]
    for i in range(3):
        for j in [i * x for x in range(len(ascii_letters))]:
            assert str(j) in texlines[i + 3]
