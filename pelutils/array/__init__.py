"""Utilities and various algorithms for working with numpy arrays.

The flagship is :func:`unique`, a drop-in for ``numpy.unique`` that runs in linear time
(rather than sorting), making it dramatically faster on large arrays.

Quick start
-----------

.. code-block:: python

    import numpy as np
    from pelutils.array import unique

    x = np.random.randint(0, 100, size=10_000_000)
    values = unique(x)
    values, index, inverse, counts = unique(
        x, return_index=True, return_inverse=True, return_counts=True,
    )

:class:`SparseGridBlobDetection` is used for detecting blobs in a sparse, N-dimensional grid.
It also works for dense grids (effetively boolean numpy arrays), which can trivially be converted
to sparse grids using ``np.where`` and ``np.column_stack``, as shown in the example.

A blob is defined as an area of touching grid entries which are all ``True``. An obvious example
is finding areas that are left in an image after thresholding on pixel values.

.. code-block:: python

    greyscale_image = ...  # Numpy array of shape height x width
    thresholded = greyscale_image > 100
    # Find the indices in the thresholded image which are True and stack them into an n x 2 array
    coords_above_threshold = np.column_stack(np.where(thresholded))

    blob_detector = SparseGridBlobDetection(coords_above_threshold)
    blobs = blob_detector.find_all_blobs()

    # The pixel coordinates in the first blob are fetched with
    coords_above_threshold[blobs[0]]

Both :func:`unique` and :class:`SparseGridBlobDetection` are implemented in C, making them
blazingly fast compared to what you usually expect from Python.
"""

from ._blob import SparseGridBlobDetection
from ._unique import unique
from ._utils import array_bytes, array_ptr

__all__ = ("SparseGridBlobDetection", "array_bytes", "array_ptr", "unique")
