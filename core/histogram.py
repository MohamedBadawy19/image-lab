"""Tasks 4, 5, 6, 8 - histogram / PDF / CDF, equalization, normalization. FROM SCRATCH."""

from dataclasses import dataclass


import numpy as np

from core.base import ImageProcessor , InvalidParameterError
from core.utils import to_float, to_uint8

@dataclass
class HistogramResult:
    hist: np.ndarray  # 256 counts
    pdf: np.ndarray  # hist / total pixels
    cdf: np.ndarray  # cumulative sum of pdf


class HistogramAnalyzer:
    name = "Analyze"
    params_schema = {}
    @staticmethod
    def analyze(channel: np.ndarray) -> HistogramResult:
        """Calculate histogram, PDF, and CDF for an image channel.

        Accepts any numeric dtype (uint8, float64, etc.) and converts to
        uint8 internally so callers don't need to pre-cast.
        """
        if not isinstance(channel, np.ndarray) or channel.size == 0:
            raise ValueError("Channel must be a non-empty NumPy array.")

        if channel.ndim != 2:
            raise ValueError("Expected a single 2D image channel.")

        channel = to_uint8(channel)

        hist = np.bincount(channel.ravel(), minlength=256)  
        pdf = to_float(hist) / channel.size
        cdf = np.cumsum(pdf)

        return HistogramResult(hist=hist, pdf=pdf, cdf=cdf)


class HistogramEqualizer(ImageProcessor):
    name = "Equalize"
    params_schema = {}

    



    def _equalize_channel(self, channel: np.ndarray, result: HistogramResult | None = None):
        # channel arrives as float64 from the pipeline — clip and cast safely
        # before using it as a LUT index (floats can't index arrays).
        channel = to_uint8(channel)
        result = result or HistogramAnalyzer.analyze(channel)
        lut = result.cdf * 255
        return lut[channel]

    def _process(self, image: np.ndarray, **params) -> np.ndarray:
        
        return self._equalize_channel(image)



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

    def _process(self, image: np.ndarray, new_min: int = 0, new_max: int = 255, **params) -> np.ndarray:
        """Min-max stretch to [new_min, new_max]. Flat image stays at new_min."""
        if not (0 <= new_min < new_max <= 255):
            raise InvalidParameterError("Require 0 <= new_min < new_max <= 255.")
        old_min = image.min()
        old_max = image.max()
        if old_max == old_min:
            return np.full_like(image, new_min, dtype=np.float64)  # _finalize casts to uint8
        stretched = (image - old_min) / (old_max - old_min) * (new_max - new_min) + new_min
        return stretched  # float64 — _finalize will clip+round+cast to uint8

        

HISTOGRAM_TOOLS = {c.name: c for c in (HistogramEqualizer, ImageNormalizer)}
