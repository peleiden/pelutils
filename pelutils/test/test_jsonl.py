import os
import pelutils.jsonl as jsonl
from pelutils.tests import MainTest

class TestJsonl(MainTest):

    def test_jsonl(self):
        data = [{ l: v } for l, v in zip(("a", "b", "c"), (1, 2, 3))]
        path = os.path.join(self.test_dir, "test.jsonl")

        # Test single block
        with open(path, "w") as f:
            jsonl.write_jsonl(iter(data), f, single_block=True)
        with open(path) as f:
            content = jsonl.load_jsonl(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test without single block
        with open(path, "w") as f:
            jsonl.write_jsonl(iter(data), f, single_block=False)
        with open(path) as f:
            content = jsonl.load_jsonl(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]
