"""Tests for core.image_data: gray formula, missing file, cached .gray property."""

import numpy as np
import pytest

from core.base import ImageLoadError
from core.image_data import ImageData


class TestGrayFormula:
    """FROM SCRATCH gray: 0.299 R + 0.587 G + 0.114 B."""

    def test_known_pixel(self):
        # Single pixel RGB image: R=100, G=150, B=200
        img = np.array([[[100, 150, 200]]], dtype=np.uint8)
        data = ImageData.from_array(img)
        gray = data.gray
        # 0.299*100 + 0.587*150 + 0.114*200 = 29.9 + 88.05 + 22.8 = 140.75 -> round -> 141
        assert gray.shape == (1, 1)
        assert gray[0, 0] == 141

    def test_pure_white(self):
        img = np.full((1, 1, 3), 255, dtype=np.uint8)
        data = ImageData.from_array(img)
        gray = data.gray
        # 0.299*255 + 0.587*255 + 0.114*255 = 255 * 1.0 = 255
        assert gray[0, 0] == 255

    def test_pure_black(self):
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        data = ImageData.from_array(img)
        assert data.gray[0, 0] == 0


class TestLoadErrors:
    """Missing file raises ImageLoadError."""

    def test_missing_file(self):
        with pytest.raises(ImageLoadError, match="not found"):
            ImageData.load("this_file_does_not_exist_12345.png")

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("not an image")
        with pytest.raises(ImageLoadError, match="Unsupported"):
            ImageData.load(str(f))


class TestGrayCaching:
    """.gray returns the same cached object on second access."""

    def test_same_object(self):
        img = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        data = ImageData.from_array(img)
        first = data.gray
        second = data.gray
        assert first is second

    def test_gray_image_returns_itself(self):
        img = np.random.randint(0, 256, (10, 10), dtype=np.uint8)
        data = ImageData.from_array(img)
        assert data.gray is img
