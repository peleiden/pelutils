from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict

from pelutils.datastorage2._pretty_json import _make_json_unsafe, _pickle_encode, _pretty_json  # pyright: ignore[reportPrivateUsage]

_T = TypeVar("_T", bound="DataStorage2")


class DataStorage2(BaseModel):
    """Better version of DataStorage based on pydantic. It makes any class fully JSON serialisable.

    Usage is very similar to DataStorage, but it has a few key advantages:
    - Allows saving and loading of nested objects.
    - Only a single file is used. Any non-json-serialisable objects are pickled and then base64-encoded to allow storing them in json files.
    - No need to decorate subclasses with @dataclass.

    Rembember that if you are using a custom model_config in a subclass, `arbitrary_types_allowed` must be True.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_safe_dump(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Dump the model as a dictionary where pickled objects have been converted to b64 strings.

        This is very similar to `self.model_dump(mode="json")` but it handles non-JSON-serialisable types.
        """
        return self.model_dump(mode="json", fallback=_pickle_encode)

    @classmethod
    def model_safe_load(cls: type[_T], safe_json: dict[str, Any]) -> _T:  # pyright: ignore[reportExplicitAny]
        """Build an instance from a safe JSON. This method is the inverse of `model_safe_dump`."""
        self_dict = _make_json_unsafe(safe_json)
        return cls.model_validate(self_dict)

    @classmethod
    def _resolve_save_file(cls, directory: str | Path, filename: str | None = None) -> Path:
        if filename is None:
            filename = cls.__name__
        return Path(directory) / f"{filename}.json"

    def save(
        self, directory: str | Path, filename: str | None = None, max_line_length: int = 140, indent: int = 2, encoding: str | None = None
    ) -> Path:
        """Save the instance to a json file in the directory. The path to the file is returned.

        If save_name is None, the path is <directory>/<class name>.json, otherwise it is <directory>/<filename>.json.
        """
        savepath = self._resolve_save_file(directory, filename)
        savepath.parent.mkdir(parents=True, exist_ok=True)
        savepath.write_text(
            _pretty_json(
                self.model_safe_dump(),
                max_line_length=max_line_length,
                indent=indent,
                # Safe should not be needed here, as the fallback function in model_dump should ensure no issues
                # However, it is kept for good measure in case there unforeseen edge cases
                safe=True,
            ),
            encoding=encoding,
        )
        return savepath

    @classmethod
    def load(cls: type[_T], directory: str | Path, filename: str | None = None, encoding: str | None = None) -> _T:
        """Load an instance from a stored json file. Arguments correspond to save method."""
        savepath = cls._resolve_save_file(directory, filename)
        with savepath.open(encoding=encoding) as f:
            self_dict = json.load(f)
        return cls.model_safe_load(self_dict)
