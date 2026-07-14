import os

from pelutils.serialization import jsonl_dump, jsonl_dumps, jsonl_load, jsonl_loads
from pelutils.tests import UnitTestCollection


class TestJsonl(UnitTestCollection):
    data = [{letter: value} for letter, value in zip(("a", "b", "c"), (1, 2, 3), strict=True)]  # noqa: RUF012

    @property
    def path(self) -> str:
        return self.get_test_path("test.jsonl")

    def test_jsonl(self):
        # Test single block
        with open(self.path, "w") as f:
            jsonl_dump(iter(self.data), f, single_block=True)
        with open(self.path) as f:
            content = jsonl_load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test without single block
        with open(self.path, "w") as f:
            jsonl_dump(iter(self.data), f, single_block=False)
        with open(self.path) as f:
            content = jsonl_load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test stringification methods
        str_repr = jsonl_dumps(self.data)
        assert str_repr == f'{{"a": 1}}{os.linesep}{{"b": 2}}{os.linesep}{{"c": 3}}'
        assert list(jsonl_loads(str_repr)) == self.data

    def test_append(self):
        data = [{letter: value} for letter, value in zip(("a", "b", "c"), (1, 2, 3), strict=True)]

        with open(self.path, "w") as f:
            jsonl_dump(data, f)
        with open(self.path, "a") as f:
            jsonl_dump(data, f)
        with open(self.path) as f:
            content = list(jsonl_load(f))

        assert content == 2 * data
