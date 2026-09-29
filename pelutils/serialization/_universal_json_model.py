import json
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict

from pelutils.serialization._pretty_json import (
    from_safe_json,
    pickle_encode,
    universal_pretty_json,
)


class UniversalJsonModel(BaseModel):
    """Pydantic BaseModel with JSON persistence for arbitrary Python values.

    Values unsupported by JSON are pickle-encoded and stored as base64 strings. Do not
    load data from an untrusted source. Custom ``model_config`` values must retain
    ``arbitrary_types_allowed=True`` if any fields on subclasses are not JSON-serialisable
    by default.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_json_dict(self, **model_dump_kwargs: Any) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Return a JSON-compatible dictionary, pickle-encoding unsupported values.

        Keyword arguments are forwarded to :meth:`pydantic.BaseModel.model_dump`, except
        ``mode`` and ``fallback``, which are fixed to preserve this method's JSON format.
        """
        if {"mode", "fallback"} & model_dump_kwargs.keys():
            raise TypeError("'mode' and 'fallback' are fixed by to_json_dict()")
        return self.model_dump(mode="json", fallback=pickle_encode, **model_dump_kwargs)

    @classmethod
    def from_json_dict(cls: type[Self], json_dict: dict[str, Any], **model_validate_kwargs: Any) -> Self:  # pyright: ignore[reportExplicitAny]
        """Build a model from :meth:`to_json_dict` output. Do not load untrusted data.

        Keyword arguments are forwarded to :meth:`pydantic.BaseModel.model_validate`.
        """
        self_dict = from_safe_json(json_dict)
        return cls.model_validate(self_dict, **model_validate_kwargs)

    def save(self, path: str | Path, *, max_line_length: int = 140, indent: int = 2, encoding: str = "utf-8"):
        """Save the model to ``path`` as human-readable JSON, creating parent directories as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            universal_pretty_json(
                self.to_json_dict(),
                max_line_length=max_line_length,
                indent=indent,
                safe=False,
            ),
            encoding=encoding,
        )

    @classmethod
    def load(cls: type[Self], path: str | Path, *, encoding: str = "utf-8") -> Self:
        """Load a model from ``path``. Do not load untrusted data."""
        with Path(path).open(encoding=encoding) as f:
            self_dict = json.load(f)
        return cls.from_json_dict(self_dict)
