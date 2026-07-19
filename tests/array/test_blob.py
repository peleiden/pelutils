import numpy as np
import pytest

from pelutils.array import SparseGridBlobDetection


class TestSparseGridBlobDetection:
    def test_error_handling(self):
        with pytest.raises(ValueError):
            SparseGridBlobDetection(np.array([[-1]]))
        with pytest.raises(TypeError):
            SparseGridBlobDetection(np.array([[1.0]]))
        with pytest.raises(ValueError):
            SparseGridBlobDetection(np.array([1]))
        SparseGridBlobDetection(np.array([[1, 2], [2, 3]], dtype=np.uint8))

    def test_simple_grid(self):
        simple_grid = np.array([0, 0, 1, 1, 1, 0])
        indices = np.column_stack(np.where(simple_grid))
        print(0)
        detector = SparseGridBlobDetection(indices)
        print(1)
        blob = detector.find_single_blob(0)
        print(2)
        assert len(blob) == 3
        assert (simple_grid[indices[blob, 0]] == 1).all()

        # Finding the same blob should cause an error as it has already been detected
        with pytest.raises(RuntimeError):
            detector.find_single_blob(1)

    def test_fancy_grid(self):
        grid = np.array([
            [1, 0, 0, 1, 1, 0],
            [1, 0, 1, 0, 1, 0],
            [1, 1, 0, 1, 1, 0],
            [0, 0, 0, 1, 0, 0],
            [1, 0, 0, 1, 0, 0],
            [1, 0, 0, 1, 1, 1],
        ])
        indices = np.column_stack(np.where(grid))
        detector = SparseGridBlobDetection(indices)
        blobs = detector.find_all_blobs()
        assert detector._visited.all()
        assert len(blobs) == 4
        assert sorted([len(blob) for blob in blobs]) == [1, 2, 4, 10]

        for blob in blobs:
            assert grid[*indices[blob].T].all()

        with pytest.raises(RuntimeError):
            detector.find_all_blobs()
        with pytest.raises(RuntimeError):
            detector.find_single_blob(0)
TestSparseGridBlobDetection().test_simple_grid()