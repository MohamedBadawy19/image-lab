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
        """np.bincount(channel.ravel(), minlength=256). Computed ONCE per channel; callers reuse it."""
        raise NotImplementedError


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
