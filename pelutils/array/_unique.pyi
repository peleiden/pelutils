from __future__ import annotations

from typing import Literal, overload

import numpy.typing as npt

from pelutils.types import AnyArray, IntArray

@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[False] = False,
    return_counts: Literal[False] = False,
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> AnyArray: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[False] = False,
    return_counts: Literal[False] = False,
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[False] = False,
    return_counts: Literal[True],
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[False] = False,
    return_counts: Literal[True],
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[True],
    return_counts: Literal[False] = False,
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[True],
    return_counts: Literal[False] = False,
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[True],
    return_counts: Literal[True],
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[False] = False,
    return_inverse: Literal[True],
    return_counts: Literal[True],
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[False] = False,
    return_counts: Literal[False] = False,
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[False] = False,
    return_counts: Literal[False] = False,
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[False] = False,
    return_counts: Literal[True],
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[False] = False,
    return_counts: Literal[True],
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[True],
    return_counts: Literal[False] = False,
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[True],
    return_counts: Literal[False] = False,
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray, list[IntArray]]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[True],
    return_counts: Literal[True],
    return_groups: Literal[False] = False,
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray, IntArray]: ...
@overload
def unique(
    array: npt.ArrayLike,
    *,
    return_index: Literal[True],
    return_inverse: Literal[True],
    return_counts: Literal[True],
    return_groups: Literal[True],
    axis: int = 0,
) -> tuple[AnyArray, IntArray, IntArray, IntArray, list[IntArray]]: ...
