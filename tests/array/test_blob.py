import numpy as np
import pytest

from pelutils.array import SparseGridBlobDetection


class TestSparseGridBlobDetection:
    simple_grid = np.array([0, 0, 1, 1, 1, 0])
    fancy_grid = np.array([
        [1, 0, 0, 1, 1, 0],
        [1, 0, 1, 0, 1, 0],
        [1, 1, 0, 1, 1, 0],
        [0, 0, 0, 1, 0, 0],
        [1, 0, 0, 1, 0, 0],
        [1, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 0, 0],
    ])

    def test_error_handling(self):
        with pytest.raises(TypeError):
            SparseGridBlobDetection(np.array([[1.0]]))
        with pytest.raises(ValueError):
            SparseGridBlobDetection(np.array([1]))
        with pytest.raises(ValueError):
            SparseGridBlobDetection(np.array([[]], dtype=int))
        SparseGridBlobDetection(np.array([[1, 2], [2, 3]], dtype=np.uint8))

    def test_empty_grid(self):
        detector = SparseGridBlobDetection(np.empty((0, 5), dtype=int))
        assert len(detector.find_all_blobs()) == 0
        with pytest.raises(RuntimeError):
            detector.find_all_blobs()
        detector = SparseGridBlobDetection(np.empty((0, 5), dtype=int))
        with pytest.raises(IndexError):
            detector.find_single_blob(0)

    def test_simple_grid(self):
        indices = np.column_stack(np.where(self.simple_grid))
        detector = SparseGridBlobDetection(indices)
        blob = detector.find_single_blob(0)
        assert len(blob) == 3
        assert (self.simple_grid[indices[blob, 0]] == 1).all()

        # Finding the same blob should cause an error as it has already been detected
        with pytest.raises(RuntimeError):
            detector.find_single_blob(1)
        with pytest.raises(RuntimeError):
            detector.find_all_blobs()

    def test_fancy_grid(self):
        indices = np.column_stack(np.where(self.fancy_grid))
        detector = SparseGridBlobDetection(indices)
        blobs = detector.find_all_blobs()
        assert detector._visited.all()
        assert len(blobs) == 4
        assert sorted([len(blob) for blob in blobs]) == [1, 2, 4, 10]

        for blob in blobs:
            assert self.fancy_grid[*indices[blob].T].all()

        with pytest.raises(RuntimeError):
            detector.find_all_blobs()
        with pytest.raises(RuntimeError):
            detector.find_single_blob(0)

    def test_negative_indices(self):
        """Test that using negative indices produce the same results."""
        indices = np.column_stack(np.where(self.fancy_grid))
        pos_detector = SparseGridBlobDetection(indices)
        neg_detector = SparseGridBlobDetection(indices - 10)
        for pos_blob, neg_blob in zip(pos_detector.find_all_blobs(), neg_detector.find_all_blobs(), strict=True):
            assert (pos_blob == neg_blob).all()

    def test_wrapping(self):
        indices = np.column_stack(np.where(self.fancy_grid))
        detector = SparseGridBlobDetection(indices, wrap_axes={1: self.fancy_grid.shape[1]})
        blobs = detector.find_all_blobs()
        assert detector._visited.all()
        assert len(blobs) == 3
        assert sorted([len(blob) for blob in blobs]) == [1, 4, 12]

        # Check that saying that the axis is larger than it is creates implicit padding, effectively preventing wrapping
        detector = SparseGridBlobDetection(indices, wrap_axes={1: self.fancy_grid.shape[1] + 1})
        blobs = detector.find_all_blobs()
        assert detector._visited.all()
        assert len(blobs) == 4
        assert sorted([len(blob) for blob in blobs]) == [1, 2, 4, 10]

        # Check that negative coordinates have no impact
        pos_detector = SparseGridBlobDetection(indices, wrap_axes={1: self.fancy_grid.shape[1]})
        neg_indices = indices.copy()
        neg_indices[:, 0] -= 2  # Subtract an arbitrary amount - results should be unaffected
        neg_indices[:, 1] -= 5 * self.fancy_grid.shape[1]  # Subtract a whole number of axis sizes
        neg_detector = SparseGridBlobDetection(neg_indices, wrap_axes={1: self.fancy_grid.shape[1]})
        for pos_blob, neg_blob in zip(pos_detector.find_all_blobs(), neg_detector.find_all_blobs(), strict=True):
            assert (pos_blob == neg_blob).all()
        assert neg_detector._visited.all()
