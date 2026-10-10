"""Tasks 4, 5, 6, 8 - histogram / PDF / CDF, equalization, normalization. FROM SCRATCH."""

from dataclasses import dataclass

import numpy as np

from core.base import ImageProcessor


@dataclass
class HistogramResult:
    hist: np.ndarray  # 256 counts
    pdf: np.ndarray  # hist / total pixels
    cdf: np.ndarray  # cumulative sum of pdf


class HistogramAnalyzer:
    @staticmethod
    def analyze(channel: np.ndarray) -> HistogramResult:
        """Calculate histogram, PDF, and CDF for a uint8 image channel."""
        if not isinstance(channel, np.ndarray) or channel.size == 0:
            raise ValueError("Channel must be a non-empty NumPy array.")

        if channel.ndim != 2:
            raise ValueError("Expected a single 2D image channel.")

        if not np.issubdtype(channel.dtype, np.integer):
            raise ValueError("Histogram analysis requires integer pixel values.")

        if np.any(channel < 0) or np.any(channel > 255):
            raise ValueError("Pixel values must be between 0 and 255.")

        hist = np.bincount(channel.ravel().astype(np.int64), minlength=256)
        pdf = hist.astype(np.float64) / channel.size
        cdf = np.cumsum(pdf)

        return HistogramResult(hist=hist, pdf=pdf, cdf=cdf)


class HistogramEqualizer(ImageProcessor):
    name = "Equalize"
    params_schema = {}

    def _process(self, image, **_):
        """new = round(CDF * 255) through a lookup table (reuse HistogramAnalyzer's CDF).
        RGB: team must choose per-channel OR luminance (Y of YCrCb) and document it."""
        raise NotImplementedError


class ImageNormalizer(ImageProcessor):
    name = "Normalize"
    params_schema = {
        "new_min": {
            "type": "int",
            "min": 0,
            "max": 254,
            "step": 1,
            "default": 0,
            "label": "New min",
        },
        "new_max": {
            "type": "int",
            "min": 1,
            "max": 255,
            "step": 1,
            "default": 255,
            "label": "New max",
        },
    }

    def _process(self, image, new_min, new_max, **_):
        """Min-max stretch. A flat image (max == min) must not divide by zero."""
        raise NotImplementedError


HISTOGRAM_TOOLS = {c.name: c for c in (HistogramEqualizer, ImageNormalizer)}
