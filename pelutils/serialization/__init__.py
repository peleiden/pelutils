from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict

from pelutils.serialization._pretty_json import _make_json_unsafe, _pickle_encode, _pretty_json  # pyright: ignore[reportPrivateUsage]

__all__ = ("UniversalJsonModel",)


class UniversalJsonModel(BaseModel):
    """Pydantic model with JSON persistence for arbitrary Python values.

    Values unsupported by JSON are pickle-encoded and stored as base64 strings. Do not
    load data from an untrusted source. Custom ``model_config`` values must retain
    ``arbitrary_types_allowed=True``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_json_dict(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Return a JSON-compatible dictionary, pickle-encoding unsupported values."""
        return self.model_dump(mode="json", fallback=_pickle_encode)

    @classmethod
    def from_json_dict(cls: type[Self], json_dict: dict[str, Any]) -> Self:  # pyright: ignore[reportExplicitAny]
        """Build a model from :meth:`to_json_dict` output. Do not load untrusted data."""
        self_dict = _make_json_unsafe(json_dict)
        return cls.model_validate(self_dict)

    def save(self, path: str | Path, *, max_line_length: int = 140, indent: int = 2, encoding: str = "utf-8") -> Path:
        """Save the model to ``path`` and return that path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _pretty_json(
                self.to_json_dict(),
                max_line_length=max_line_length,
                indent=indent,
                safe=False,
            ),
            encoding=encoding,
        )
        return path

    @classmethod
    def load(cls: type[Self], path: str | Path, *, encoding: str = "utf-8") -> Self:
        """Load a model from ``path``. Do not load untrusted data."""
        with Path(path).open(encoding=encoding) as f:
            self_dict = json.load(f)
        return cls.from_json_dict(self_dict)
