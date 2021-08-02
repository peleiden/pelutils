from __future__ import annotations

import pytest

from pelutils.tests import MainTest
from pelutils.parser import Argument, Option, Flag


class TestParser(MainTest):

    def test_argument_validation(self):
        with pytest.raises(ValueError):
            Argument("")
        with pytest.raises(ValueError):
            Option("--Hello there", default="General Kenobi")
        with pytest.raises(ValueError):
            Flag("show-memes", abbrv="sm")
        with pytest.raises(ValueError):
            Option("memes", abbrv="-s", default="doge")
        Argument("meme-folder")
        Option("memes", abbrv="m", default="doge")
        Flag("show-memes", abbrv="s")
