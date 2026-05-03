import numpy as np

from pelutils import AnyArray, BoolArray, ComplexArray, FloatArray, IntArray


def function_which_takes_np_types(
    any_array: AnyArray,
    bool_array: BoolArray,
    complex_array: ComplexArray,
    float_array: FloatArray,
    int_array: IntArray,
) -> ComplexArray:
    return any_array + bool_array + complex_array + float_array + int_array


def test_types():
    """There isn't much to test.

    Just make sure that using the types doesn't break anything silly like function declarations.
    """
    any_array = np.arange(5, dtype=np.float16)
    bool_array = np.arange(5).astype(bool)
    complex_array = 1j * np.arange(5)
    float_array = np.arange(5, dtype=np.float32)
    int_array = np.arange(5)
    function_which_takes_np_types(any_array, bool_array, complex_array, float_array, int_array)
