"""Task 3 - edge detection. Detectors work on the GRAY image and return gx, gy and magnitude."""

from dataclasses import dataclass

import numpy as np
import cv2
from core.base import ImageProcessor, InvalidParameterError
from core.utils import convolve 


@dataclass
class EdgeResult:
    gx: np.ndarray | None  # None for Canny
    gy: np.ndarray | None  # None for Canny
    magnitude: np.ndarray  # uint8 0-255 for display

def to_display(values: np.ndarray) -> np.ndarray:
    """Float gradient (can be negative) -> uint8 image 0..255 for showing."""
    values = np.abs(values)
    peak = values.max()
    if peak == 0:                          # no edges at all
        return np.zeros(values.shape, dtype=np.uint8)
    return (values / peak * 255).astype(np.uint8)

class EdgeDetector(ImageProcessor):
    """Subclasses implement _process(gray) -> EdgeResult. _finalize returns the result unchanged."""
    name: str
    params_schema: dict = {}
    has_xy = True  # False for Canny: the GUI hides the X/Y panels

    def _finalize(self, out):
        return out

    def detect(self, gray: np.ndarray, **params) -> EdgeResult:
        if gray.ndim != 2:
            raise InvalidParameterError("Gray image must be 2D.")
        return self._process(gray, **params)


class GradientDetector(EdgeDetector):
    """Shared logic for Sobel / Prewitt / Roberts. Subclasses only define the kernels."""

    kernel_x: np.ndarray
    kernel_y: np.ndarray

    def _process(self, gray: np.ndarray, **_) -> EdgeResult:
        gx = convolve(gray, self.kernel_x)  # float, may be negative
        gy = convolve(gray, self.kernel_y)
        magnitude = np.hypot(gx, gy)
        return EdgeResult(to_display(gx), to_display(gy), to_display(magnitude))

class SobelDetector(GradientDetector):
    name = "Sobel"
    
    kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float)
    kernel_y = kernel_x.T

    


class PrewittDetector(GradientDetector):
    name = "Prewitt"
    
    kernel_x = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=float)
    kernel_y = kernel_x.T

    


class RobertsDetector(GradientDetector):
    name = "Roberts"
   
    kernel_x = np.array([[1, 0], [0, -1]], dtype=float)
    kernel_y = np.array([[0, 1], [-1, 0]], dtype=float)

    


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
    def _process(self, gray: np.ndarray, low: int = 100, high: int = 200, **_) -> EdgeResult:
        if not (0 <= low < high <= 255):
            raise InvalidParameterError("Low and high thresholds must be between 0 and 255.")
        # cv2.Canny requires uint8. detect() passes the gray image directly,
        # but if this is ever called via apply() the input will be float64.
        gray_u8 = np.clip(np.round(gray), 0, 255).astype(np.uint8)
        return EdgeResult(None, None, cv2.Canny(gray_u8, low, high))

        


EDGES = {c.name: c for c in (SobelDetector, PrewittDetector, RobertsDetector, CannyDetector)}
