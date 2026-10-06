"""Task 3 - edge detection. Detectors work on the GRAY image and return gx, gy and magnitude."""

from dataclasses import dataclass

import numpy as np

from core.base import ImageProcessor


@dataclass
class EdgeResult:
    gx: np.ndarray | None  # None for Canny
    gy: np.ndarray | None  # None for Canny
    magnitude: np.ndarray  # uint8 0-255 for display


class EdgeDetector(ImageProcessor):
    """Subclasses implement _process(gray) -> EdgeResult. _finalize returns the result unchanged."""

    has_xy = True  # False for Canny: the GUI hides the X/Y panels

    def _finalize(self, out):
        return out

    def detect(self, gray: np.ndarray, **params) -> EdgeResult:
        return self.apply(gray, **params)


class SobelDetector(EdgeDetector):
    name = "Sobel"
    params_schema = {}

    def _process(self, image, **_):
        raise NotImplementedError


class PrewittDetector(EdgeDetector):
    name = "Prewitt"
    params_schema = {}

    def _process(self, image, **_):
        raise NotImplementedError


class RobertsDetector(EdgeDetector):
    name = "Roberts"
    params_schema = {}

    def _process(self, image, **_):
        raise NotImplementedError


class CannyDetector(EdgeDetector):
    """OpenCV allowed here ONLY (cv2.Canny)."""

    name = "Canny"
    has_xy = False
    params_schema = {
        "low": {
            "type": "int",
            "min": 0,
            "max": 255,
            "step": 1,
            "default": 100,
            "label": "Low threshold",
        },
        "high": {
            "type": "int",
            "min": 0,
            "max": 255,
            "step": 1,
            "default": 200,
            "label": "High threshold",
        },
    }

    def _process(self, image, low, high, **_):
        raise NotImplementedError


EDGES = {c.name: c for c in (SobelDetector, PrewittDetector, RobertsDetector, CannyDetector)}
