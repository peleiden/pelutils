import os
import pelutils.jsonl as jsonl
from pelutils.tests import MainTest


class TestJsonl(MainTest):

    def test_jsonl(self):
        data = [{ l: v } for l, v in zip(("a", "b", "c"), (1, 2, 3))]
        path = os.path.join(self.test_dir, "test.jsonl")

        # Test single block
        with open(path, "w") as f:
            jsonl.dump(iter(data), f, single_block=True)
        with open(path) as f:
            content = jsonl.load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test without single block
        with open(path, "w") as f:
            jsonl.dump(iter(data), f, single_block=False)
        with open(path) as f:
            content = jsonl.load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test stringification methods
        str_repr = jsonl.dumps(data)
        assert str_repr == '{"a":1}\n{"b":2}\n{"c":3}'
        assert list(jsonl.loads(str_repr)) == data
