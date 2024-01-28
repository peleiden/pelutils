import os
import pelutils.jsonl as jsonl
from pelutils.tests import UnitTestCollection


class TestJsonl(UnitTestCollection):

    data = [{ l: v } for l, v in zip(("a", "b", "c"), (1, 2, 3))]
    path = os.path.join(UnitTestCollection.test_dir, "test.jsonl")

    def test_jsonl(self):

        # Test single block
        with open(self.path, "w") as f:
            jsonl.dump(iter(self.data), f, single_block=True)
        with open(self.path) as f:
            content = jsonl.load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test without single block
        with open(self.path, "w") as f:
            jsonl.dump(iter(self.data), f, single_block=False)
        with open(self.path) as f:
            content = jsonl.load(f)
            assert list(content) == [{"a": 1}, {"b": 2}, {"c": 3}]

        # Test stringification methods
        str_repr = jsonl.dumps(self.data)
        assert str_repr == '{"a":1}%s{"b":2}%s{"c":3}' % (os.linesep, os.linesep)
        assert list(jsonl.loads(str_repr)) == self.data

    def test_append(self):
        data = [{ l: v } for l, v in zip(("a", "b", "c"), (1, 2, 3))]

        with open(self.path, "w") as f:
            jsonl.dump(data, f)
        with open(self.path, "a") as f:
            jsonl.dump(data, f)
        with open(self.path) as f:
            content = list(jsonl.load(f))

        assert content == 2 * data
