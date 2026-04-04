"""Tests for pretty_json."""

from __future__ import annotations

import json

import pytest

from pelutils.pretty_json import pretty_json

# ─── Helpers ────────────────────────────────────────────────────────────────


def _roundtrip(obj: dict | list, **kwargs) -> dict | list:
    """pretty_json → json.loads — the parsed result must be valid JSON."""
    return json.loads(pretty_json(obj, **kwargs))


# ─── Basic structure ────────────────────────────────────────────────────────


class TestBasicStructures:
    def test_simple_dict(self) -> None:
        result = pretty_json({"a": 1, "b": 2})
        assert result == '{\n  "a": 1,\n  "b": 2\n}'

    def test_simple_list_packed_on_one_line(self) -> None:
        """Short primitive lists pack onto a single indented line."""
        result = pretty_json([1, 2, 3])
        assert result == "[\n  1, 2, 3\n]"

    def test_empty_dict(self) -> None:
        assert pretty_json({}) == "{}"

    def test_empty_list(self) -> None:
        assert pretty_json([]) == "[]"

    def test_single_element_dict(self) -> None:
        result = pretty_json({"only": True})
        assert result == '{\n  "only": true\n}'

    def test_single_element_list(self) -> None:
        result = pretty_json(["solo"])
        assert result == '[\n  "solo"\n]'


# ─── Primitive types ───────────────────────────────────────────────────────


class TestPrimitives:
    @pytest.mark.parametrize(
        "value, expected_fragment",
        [
            ("hello", '"hello"'),
            (42, "42"),
            (3.14, "3.14"),
            (True, "true"),
            (False, "false"),
            (None, "null"),
        ],
    )
    def test_primitive_values(self, value: object, expected_fragment: str) -> None:
        result = pretty_json({"v": value})
        assert expected_fragment in result

    def test_bool_is_not_int(self) -> None:
        result = pretty_json({"flag": True})
        assert "true" in result
        assert ": 1" not in result


# ─── Inline vs. expanded logic ─────────────────────────────────────────────


class TestInlineExpand:
    def test_nested_dict_stays_inline(self) -> None:
        obj = {"user": {"name": "Alice", "age": 30}}
        result = pretty_json(obj)
        assert '{"name": "Alice", "age": 30}' in result

    def test_nested_dict_expands_when_too_long(self) -> None:
        obj = {"user": {"name": "Alice", "age": 30}}
        result = pretty_json(obj, max_line_length=30)
        assert '"name": "Alice"' in result
        assert '"age": 30' in result
        assert result.count("\n") >= 4

    def test_nested_list_stays_inline(self) -> None:
        obj = {"nums": [1, 2, 3]}
        result = pretty_json(obj)
        assert "[1, 2, 3]" in result

    def test_nested_list_packs_when_too_long(self) -> None:
        """A 20-element list should bin-pack, not one-per-line."""
        obj = {"nums": list(range(20))}
        result = pretty_json(obj, max_line_length=40)
        # Must have expanded (not inline) but not 20+ lines.
        lines = result.strip().split("\n")
        # Bin-packing: far fewer lines than 20.
        assert len(lines) < 15
        # But must still be valid.
        assert _roundtrip(obj, max_line_length=40) == obj

    def test_root_always_expanded_even_if_short(self) -> None:
        result = pretty_json({"a": 1})
        assert "\n" in result

    def test_inline_respects_key_length(self) -> None:
        short_key = {"k": {"a": 1, "b": 2, "c": 3}}
        long_key = {"a_really_long_key_name": {"a": 1, "b": 2, "c": 3}}
        limit = 45
        short_result = pretty_json(short_key, max_line_length=limit)
        long_result = pretty_json(long_key, max_line_length=limit)
        assert short_result.count("\n") < long_result.count("\n")


# ─── Bin-packing primitive lists ───────────────────────────────────────────


class TestBinPacking:
    def test_all_fit_one_line(self) -> None:
        result = pretty_json([1, 2, 3, 4, 5])
        assert result == "[\n  1, 2, 3, 4, 5\n]"

    def test_wraps_at_limit(self) -> None:
        obj = list(range(10))
        result = pretty_json(obj, max_line_length=20)
        parsed = json.loads(result)
        assert parsed == obj
        # Every line must respect the limit.
        for line in result.split("\n"):
            assert len(line) <= 20, f"Line too long: {line!r}"

    def test_wraps_with_strings(self) -> None:
        obj = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        result = pretty_json(obj, max_line_length=30)
        parsed = json.loads(result)
        assert parsed == obj
        for line in result.split("\n"):
            assert len(line) <= 30, f"Line too long: {line!r}"

    def test_single_long_string_overflows_gracefully(self) -> None:
        """An irreducibly long item is placed alone and allowed to overflow."""
        long = "x" * 200
        result = pretty_json([long], max_line_length=80)
        parsed = json.loads(result)
        assert parsed == [long]

    def test_mixed_list_not_packed(self) -> None:
        """Lists with nested containers use one-element-per-line, not packing."""
        obj = [[1, 2], [3, 4], [5, 6]]
        result = pretty_json(obj, max_line_length=40)
        # Each sub-list should be on its own line.
        assert result.count("\n") == len(obj) + 1  # open + items + close

    def test_nested_primitive_list_packs(self) -> None:
        obj = {"data": list(range(30))}
        result = pretty_json(obj, max_line_length=50)
        parsed = json.loads(result)
        assert parsed == obj
        # Far fewer lines than 30 elements.
        assert result.count("\n") < 20

    def test_narrow_limit_one_per_line(self) -> None:
        """With a very narrow limit, packing degrades to one item per line."""
        obj = [100, 200, 300]
        result = pretty_json(obj, max_line_length=8)
        assert result == "[\n  100,\n  200,\n  300\n]"

    def test_packing_produces_fewer_lines_than_narrow(self) -> None:
        obj = list(range(50))
        wide = pretty_json(obj, max_line_length=120)
        narrow = pretty_json(obj, max_line_length=25)
        assert wide.count("\n") < narrow.count("\n")

    def test_bool_none_mix_still_packs(self) -> None:
        obj = [True, False, None, 1, "hi"]
        result = pretty_json(obj)
        # All primitives → should be packed (and fit on one line at width 120).
        assert result == '[\n  true, false, null, 1, "hi"\n]'

    def test_packing_inside_dict_value(self) -> None:
        obj = {"matrix_row": list(range(15))}
        result = pretty_json(obj, max_line_length=60)
        parsed = json.loads(result)
        assert parsed == obj
        # The list should be packed, not inline (too long) and not 15 lines.
        list_lines = [line for line in result.split("\n") if line.strip().startswith(("0", "1"))]
        assert 0 < len(list_lines) < 15


# ─── Nesting depth ─────────────────────────────────────────────────────────


class TestNesting:
    def test_deeply_nested(self) -> None:
        obj: dict = {"a": {"b": {"c": {"d": "leaf"}}}}
        assert _roundtrip(obj, max_line_length=30) == obj

    def test_list_of_dicts(self) -> None:
        obj = [{"id": i, "v": f"item_{i}"} for i in range(5)]
        result = pretty_json(obj)
        for i in range(5):
            assert f'"id": {i}' in result
        assert _roundtrip(obj) == obj

    def test_dict_of_lists(self) -> None:
        obj = {"evens": [0, 2, 4], "odds": [1, 3, 5]}
        result = pretty_json(obj)
        assert "[0, 2, 4]" in result
        assert "[1, 3, 5]" in result

    def test_mixed_nesting(self) -> None:
        obj = {
            "name": "project",
            "tags": ["python", "json"],
            "meta": {"version": 1, "flags": [True, False]},
        }
        assert _roundtrip(obj) == obj

    def test_nested_empty_containers(self) -> None:
        obj = {"empty_d": {}, "empty_l": [], "nested": {"inner": {}}}
        result = pretty_json(obj)
        assert _roundtrip(obj) == obj
        assert "{}" in result
        assert "[]" in result


# ─── Formatting options ────────────────────────────────────────────────────


class TestOptions:
    def test_custom_indent_size_4(self) -> None:
        result = pretty_json({"a": 1}, indent=4)
        assert result == '{\n    "a": 1\n}'

    def test_custom_indent_size_0(self) -> None:
        result = pretty_json({"a": 1, "b": 2}, indent=0)
        assert result == '{\n"a": 1,\n"b": 2\n}'

    def test_shorter_max_line_produces_more_lines(self) -> None:
        obj = {"k": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
        short = pretty_json(obj, max_line_length=20)
        long = pretty_json(obj, max_line_length=200)
        assert short.count("\n") > long.count("\n")


# ─── Round-trip validity ───────────────────────────────────────────────────


class TestRoundtrip:
    SAMPLES: list[dict | list] = (
        {},
        [],
        {"a": 1},
        [1, "two", None, True, False, 3.14],
        {"nested": {"deep": {"deeper": [1, 2, 3]}}},
        [{"id": i, "data": {"x": i * 10}} for i in range(8)],
        {"unicode": "café ☕ 日本語 🎉"},
        {"special_chars": 'quote"inside\\and\nnewline'},
        {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]},
    )

    @pytest.mark.parametrize("obj", SAMPLES)
    def test_roundtrip(self, obj: dict | list) -> None:
        assert _roundtrip(obj) == obj

    @pytest.mark.parametrize("obj", SAMPLES)
    def test_roundtrip_narrow(self, obj: dict | list) -> None:
        assert _roundtrip(obj, max_line_length=30) == obj


# ─── Edge cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_long_string_exceeds_limit_gracefully(self) -> None:
        obj = {"k": "a" * 200}
        assert _roundtrip(obj, max_line_length=80) == obj

    def test_unicode_preserved(self) -> None:
        result = pretty_json({"emoji": "🎉", "jp": "こんにちは"})
        assert "🎉" in result
        assert "こんにちは" in result

    def test_tuple_treated_as_list(self) -> None:
        obj = {"coords": (1, 2, 3)}  # type: ignore[dict-item]
        parsed = json.loads(pretty_json(obj))  # type: ignore[arg-type]
        assert parsed == {"coords": [1, 2, 3]}

    def test_respects_line_length(self) -> None:
        obj = {
            "users": [
                {"name": "Alice", "email": "alice@example.com", "age": 30},
                {"name": "Bob", "email": "bob@example.com", "age": 25},
            ],
            "count": 2,
        }
        limit = 80
        result = pretty_json(obj, max_line_length=limit)
        for line in result.split("\n"):
            assert len(line) <= limit, f"Line too long ({len(line)}): {line!r}"
