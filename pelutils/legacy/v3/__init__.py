"""Legacy module for preserving functionality that no longer has a place in pelutils, but is hard to change.

This is especially relevant for functionality which leaves persistent data which may need to be loaded in later.
``DataStorage`` is the obvious example here as it defines a custom serialisation/deserialisation protocol.
Upgrading to pelutils 4 without this module would make old persisted ``DataStorage`` instances impossible to load.
"""

from ._datastorage import DataStorage

__all__ = ("DataStorage",)
