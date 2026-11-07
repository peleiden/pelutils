from pydantic import BaseModel

from pelutils.misc import pformat


class Inner(BaseModel):
    x: list[int]
    name: str


class Outer(BaseModel):
    inner: Inner
    by_key: dict[str, Inner]


def test_pformat_short_model():
    model = Inner(x=[1], name="a")
    assert pformat(model) == repr(model)


def test_pformat_nested_model():
    model = Outer(inner=Inner(x=[1, 2], name="a" * 30), by_key={"k": Inner(x=[], name="b")})
    assert pformat(model, width=40) == (
        "Outer(\n"
        "    inner=Inner(\n"
        "        x=[1, 2],\n"
        "        name='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'\n"
        "    ),\n"
        "    by_key={\n"
        "        'k': Inner(x=[], name='b')\n"
        "    }\n"
        ")"
    )


def test_pformat_plain_dict():
    assert pformat({"b": [1, 2], "a": "x" * 30}, width=20) == "{\n    'b': [1, 2],\n    'a': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'\n}"
