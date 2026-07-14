import os

from pelutils.jsonl import dump, dumps, load, loads
from pelutils.tests import UnitTestCollection


class TestJsonl(UnitTestCollection):
    data = [{letter: value} for letter, value in zip(("a", "b", "c"), (1, 2, 3), strict=True)]  # noqa: RUF012

    @property
    def path(self) -> str:
        return self.get_test_path("test.jsonl")

    def test_jsonl(self):
        # Test single block
        with open(self.path, "w") as f:
            dump(iter(self.data), f, single_block=True)
        with open(self.path) as f:
            content = load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test without single block
        with open(self.path, "w") as f:
            dump(iter(self.data), f, single_block=False)
        with open(self.path) as f:
            content = load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test stringification methods
        str_repr = dumps(self.data)
        assert str_repr == f'{{"a":1}}{os.linesep}{{"b":2}}{os.linesep}{{"c":3}}'
        assert list(loads(str_repr)) == self.data

    def test_append(self):
        data = [{letter: value} for letter, value in zip(("a", "b", "c"), (1, 2, 3), strict=True)]

        with open(self.path, "w") as f:
            dump(data, f)
        with open(self.path, "a") as f:
            dump(data, f)
        with open(self.path) as f:
            content = list(load(f))

        assert content == 2 * data
