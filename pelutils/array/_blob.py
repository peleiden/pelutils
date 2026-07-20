from __future__ import annotations

import ctypes

import _pelutils_c as _c
import numpy as np

import pelutils._c as c_utils
from pelutils.types import IntArray


class SparseGridBlobDetection:
    """Detect blobs (continuous regions) in a sparse grid implemented in C for high performance.

    The grids can have an arbitrary number of dimensions, but a common usecase might be in image analysis.
    Imaging thresholding an image based on pixel values. This class offers blazingly fast detection of all
    blobs in the resulting boolean image.

    While images are a prime use case, this class works for any dimensionality of arrays.
    It provides two methods: ``find_all_blobs`` and ``find_single_blob``. The first, as demonstrated above, detects,
    for each blobs, all pixels belonging to that blob. The second finds only a single blob and requires a starting pixel.

    Adjacency is defined by a plus-shaped kernel (generalised to the dimensions of the array), not a solid square-shaped
    kernel. To get the behaviour of a square-shaped kernel, run a dilation with a square kernel over the array first.

    Note that this class is stateful, meaning that for each call to either of the afforementioned methods, trying to
    detected an already detected blob will raise a ``RuntimeError``.
    """

    def __init__(self, grid_coords: IntArray):
        """Initialise the blob detection.

        ``grid_coords`` represents the nodes in a grid that are part of a blob. For an ``d``-dimensional
        grid, it has shape ``n x d`` where ``n`` is the number of nodes in the grid belonging to any blob.
        Here, a grid is effectively a boolean numpy array, and nodes its entries.
        """
        self._validate_grid_coords(grid_coords)

        # Ensure correct dtype and make a copy to prevent outside changes to the array unintentionally causing a ruckus
        self._grid_coords = grid_coords.astype(np.int64).copy()
        # Boolean array of visited nodes
        # After each call to `find_blob`, the found indices are set to True
        self._visited = np.zeros(len(self._grid_coords), dtype=bool)
        # Next row in _grid_coords from which to start a search
        self._next_index = 0
        # Set to True when all coordinates have been visited
        self._done = False

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            # The pointers array is used to store pointers from objects allocated in the C code and pass them between calls
            # This is very ugly and hacky but it works and is arguably simpler that using the Python C API correctly in this
            # use case - at least I'm lazy enough to assume so
            # This first element is the pointer to the coord-to-index hashmap
            self._pointers = np.empty(1, dtype=np.uint64)
        else:
            # If pointers are not eight bytes, it is probably a thirty-two bit system, so uint32 is used to store pointers
            # 32-bit systems are not officially supported, but this probably works
            self._pointers = np.empty(1, dtype=np.uint32)

        self._index_args = c_utils.get_array_c_args(self._grid_coords)
        self._pointer_args = c_utils.get_array_c_args(self._pointers)
        _c.build_lookup_table(
            self._pointer_args.array_ptr,
            self._index_args.array_ptr,
            self._grid_coords.shape[0],
            self._grid_coords.shape[1],
        )

    def _validate_grid_coords(self, grid_coords: IntArray):
        """Raise an exception if given ``grid_coords`` are invalid."""
        if not np.issubdtype(grid_coords.dtype, np.integer):
            raise TypeError(f"`grid_coords` must have an integer dtype, not {grid_coords.dtype}")
        if len(grid_coords.shape) != 2:
            raise ValueError(f"`grid_coords` must have shape n x d but has {len(grid_coords.shape)} axes")
        if grid_coords.shape[1] == 0:
            raise ValueError("Coordinates cannot be 0-dimensional")

    def _mark_visited(self, indices: IntArray) -> bool:
        self._visited[indices] = True
        while self._next_index < len(self._visited) and self._visited[self._next_index]:
            self._next_index += 1
        self._done = self._next_index == len(self._visited)
        return self._done

    def find_single_blob(self, init_index: int) -> IntArray:
        """Detect a single blob starting at ``grid_coords[init_index]``.

        Return the index of each row in ``grid_coords`` which is part of the blob.
        """
        if self._visited[init_index]:
            raise RuntimeError(f"Blob at index {init_index} ({self._grid_coords[init_index]}) has already been visited")
        blob_indices: list[int] = list()
        _c.find_blob(
            self._pointer_args.array_ptr,
            self._index_args.array_ptr,
            init_index,
            self._grid_coords.shape[0],
            self._grid_coords.shape[1],
            blob_indices,
        )

        blob_indices_arr = np.array(blob_indices)
        self._mark_visited(blob_indices_arr)
        return blob_indices_arr

    def find_all_blobs(self) -> list[IntArray]:
        """Detect all blobs in ``grid_coords``.

        For each detected blob, an array is returned containing the rows in ``grid_coords`` which are part of that blob.
        """
        if self._done:
            raise RuntimeError("Blob detection has already been run")

        indices = np.array([], dtype=np.int64)
        blobs: list[IntArray] = list()
        while not self._mark_visited(indices):
            indices = self.find_single_blob(self._next_index)
            blobs.append(indices)

        return blobs

    def __del__(self):
        """Free the lookup table when the instance is no longer referenced to prevent memory leak."""
        try:
            _c.free_lookup_table(self._pointer_args.array_ptr)
        except AttributeError:
            # If the error happens early in init (e.g. wrong call to __init__), _pointer_args has not yet been defined,
            # and the hashmap has not been created
            pass
