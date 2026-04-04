import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from pelutils.datastorage2._pretty_json import _PICKLE_PREFIX, _decode_unpickle, _pretty_json


def pretty_json_with_defaults(obj: Any) -> Any:
    return _pretty_json(
        obj,
        max_line_length=140,
        indent=2,
        safe=True,
    )


# ─── Pickle / b64 fallback ─────────────────────────────────────────────────


@dataclass
class _Point:
    x: float
    y: float


class TestPickleFallback:
    def test_datetime_is_pickled(self) -> None:
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = pretty_json_with_defaults({"ts": dt})
        parsed = json.loads(result)
        assert parsed["ts"].startswith(_PICKLE_PREFIX)
        assert _decode_unpickle(parsed["ts"]) == dt

    def test_dataclass_is_pickled(self) -> None:
        pt = _Point(1.5, 2.5)
        result = pretty_json_with_defaults({"point": pt})
        parsed = json.loads(result)
        restored = _decode_unpickle(parsed["point"])
        assert restored == pt

    def test_decimal_is_pickled(self) -> None:
        obj = {"price": Decimal("19.99")}
        result = pretty_json_with_defaults(obj)
        parsed = json.loads(result)
        assert _decode_unpickle(parsed["price"]) == Decimal("19.99")

    def test_path_is_pickled(self) -> None:
        p = Path("/usr/local/bin")
        result = pretty_json_with_defaults({"path": p})
        parsed = json.loads(result)
        assert _decode_unpickle(parsed["path"]) == p

    def test_set_inside_list_is_pickled(self) -> None:
        obj = [1, {2, 3, 4}, "hello"]
        result = pretty_json_with_defaults(obj)
        parsed = json.loads(result)
        assert parsed[0] == 1
        assert parsed[2] == "hello"
        assert _decode_unpickle(parsed[1]) == {2, 3, 4}

    def test_nested_non_serialisable(self) -> None:
        obj = {"outer": {"inner": _Point(0, 0)}}
        result = pretty_json_with_defaults(obj)
        parsed = json.loads(result)
        assert _decode_unpickle(parsed["outer"]["inner"]) == _Point(0, 0)

    def test_unpickle_rejects_plain_string(self) -> None:
        with pytest.raises(ValueError, match="Not a pickled value"):
            _decode_unpickle("just a string")

    def test_non_string_dict_keys_coerced(self) -> None:
        obj = {1: "one", 2: "two"}  # type: ignore[dict-item]
        result = pretty_json_with_defaults(obj)  # type: ignore[arg-type]
        parsed = json.loads(result)
        assert parsed == {"1": "one", "2": "two"}

    def test_output_is_valid_json_with_mixed_types(self) -> None:
        obj = {
            "name": "test",
            "when": datetime(2025, 6, 1),
            "tags": ["a", "b"],
            "nested": {"d": Decimal("1.1"), "n": None},
        }
        parsed = json.loads(pretty_json_with_defaults(obj))
        assert parsed["name"] == "test"
        assert parsed["tags"] == ["a", "b"]
        assert parsed["nested"]["n"] is None
