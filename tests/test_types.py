import numpy as np

from pelutils.types import AnyArray, FloatArray, IntArray


def function_which_takes_np_types(
    any_array: AnyArray,
    float_array: FloatArray,
    int_array: IntArray,
) -> FloatArray:
    return any_array + float_array + int_array


def test_types():
    """There isn't much to test.

    Just make sure that using the types doesn't break anything silly like function declarations.
    """
    any_array = np.arange(5, dtype=np.float16)
    float_array = np.arange(5, dtype=np.float32)
    int_array = np.arange(5)
    function_which_takes_np_types(any_array, float_array, int_array)
