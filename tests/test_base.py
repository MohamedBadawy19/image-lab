"""Tests for core.base: ImageProcessor validation and defaults."""

import numpy as np
import pytest

from core.base import ImageProcessor, InvalidParameterError, UnsupportedImageError


class DummyProcessor(ImageProcessor):
    """Minimal concrete subclass for testing the base class."""

    name = "Dummy"
    params_schema = {
        "value": {"type": "int", "min": 0, "max": 100, "step": 1, "default": 50, "label": "Val"},
    }

    def _process(self, image, value=50, **_):
        return image.astype(np.float64) + value


class TestWithDefaults:
    """_with_defaults fills missing params from schema defaults."""

    def test_fills_default(self):
        proc = DummyProcessor()
        merged = proc._with_defaults({})
        assert merged == {"value": 50}

    def test_user_overrides_default(self):
        proc = DummyProcessor()
        merged = proc._with_defaults({"value": 10})
        assert merged == {"value": 10}


class TestValidation:
    """_validate raises InvalidParameterError for out-of-range params."""

    def test_rejects_empty_array(self):
        proc = DummyProcessor()
        with pytest.raises(UnsupportedImageError):
            proc.apply(np.array([]))

    def test_rejects_below_min(self):
        proc = DummyProcessor()
        img = np.zeros((10, 10), dtype=np.uint8)
        with pytest.raises(InvalidParameterError, match=">="):
            proc.apply(img, value=-1)

    def test_rejects_above_max(self):
        proc = DummyProcessor()
        img = np.zeros((10, 10), dtype=np.uint8)
        with pytest.raises(InvalidParameterError, match="<="):
            proc.apply(img, value=200)

    def test_valid_params_pass(self):
        proc = DummyProcessor()
        img = np.zeros((10, 10), dtype=np.uint8)
        result = proc.apply(img, value=10)
        assert result.dtype == np.uint8
        assert np.all(result == 10)


class TestApply:
    """apply() fills defaults, validates, processes, and finalizes."""

    def test_clips_and_casts(self):
        proc = DummyProcessor()
        img = np.full((5, 5), 250, dtype=np.uint8)
        result = proc.apply(img, value=20)
        # 250 + 20 = 270 -> clipped to 255
        assert np.all(result == 255)
        assert result.dtype == np.uint8

    def test_default_param_used(self):
        proc = DummyProcessor()
        img = np.zeros((5, 5), dtype=np.uint8)
        result = proc.apply(img)
        assert np.all(result == 50)
