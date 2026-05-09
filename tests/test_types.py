import numpy as np

from pelutils import AnyArray, BoolArray, ComplexArray, FloatArray, IntArray, StringArray
from pelutils.types import BytesArray, ObjectArray


def function_which_takes_np_types(  # noqa: PLR0913
    any_array: AnyArray,
    bool_array: BoolArray,
    bytes_array: BytesArray,
    complex_array: ComplexArray,
    float_array: FloatArray,
    int_array: IntArray,
    object_array: ObjectArray,
    string_array: StringArray,
) -> ComplexArray:
    assert np.issubdtype(object_array.dtype, np.object_)
    assert not np.issubdtype(bytes_array.dtype, np.object_)
    assert not np.issubdtype(string_array.dtype, np.object_)
    assert not np.issubdtype(float_array.dtype, np.object_)
    return any_array + bool_array + complex_array + float_array + int_array + len(bytes_array) + len(string_array)


def test_types():
    """There isn't much to test.

    Just make sure that using the types doesn't break anything silly like function declarations.
    """
    any_array = np.arange(5, dtype=np.float16)
    bool_array = np.arange(5).astype(bool)
    bytes_array = np.array([x.to_bytes(x, "little") for x in list(range(5))])
    complex_array = 1j * np.arange(5)
    float_array = np.arange(5, dtype=np.float32)
    int_array = np.arange(5)
    string_array = np.array([str(x) for x in list(range(5))])
    object_array = np.array([str, "", 1, 2, object, object()])
    function_which_takes_np_types(any_array, bool_array, bytes_array, complex_array, float_array, int_array, object_array, string_array)
