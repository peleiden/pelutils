from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

from pelutils.datastorage2._pretty_json import _make_json_unsafe, _pretty_json  # pyright: ignore[reportPrivateUsage]

_T = TypeVar("_T", bound="DataStorage2")


class DataStorage2(BaseModel):
    """Better version of DataStorage based on pydantic.

    Usage is very similar to DataStorage, but it has a few key advantages:
    - Allows saving and loading of nested objects.
    - Only a single file is used. Any non-json-serialisable objects are pickled and then base64-encoded to allow storing them in json files.
    - No need to decorate subclasses with @dataclass.

    Rembember that if you are using a custom model_config in a subclass, `arbitrary_types_allowed` must be True.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def _resolve_save_file(cls, directory: str | Path, filename: str | None = None) -> Path:
        if filename is None:
            filename = cls.__name__
        return Path(directory) / f"{filename}.json"

    def save(
        self, directory: str | Path, filename: str | None = None, max_line_length: int = 140, indent: int = 2, encoding: str | None = None
    ) -> Path:
        """Save the instance to a json file in the directory. The path to the file is returned.

        If save_name is None, the path is <directory>/<class name>.json, otherwise it is <directory>/<save_name>.json.
        """
        savepath = self._resolve_save_file(directory, filename)
        self_dict = self.model_dump()
        savepath.write_text(
            _pretty_json(
                self_dict,
                max_line_length=max_line_length,
                indent=indent,
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
        self_dict = _make_json_unsafe(self_dict)
        return cls.model_validate(self_dict)
