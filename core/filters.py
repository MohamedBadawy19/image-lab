"""Task 2 - low pass filters, FROM SCRATCH. convolve() is shared by filters AND edge detectors."""

import numpy as np

from core.base import ImageProcessor


def convolve(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Gray or RGB (per channel), reflect padding, non-square kernels allowed (Roberts 2x2),
    vectorized with sliding_window_view. Returns FLOAT, no clipping."""
    raise NotImplementedError


def mse(a: np.ndarray, b: np.ndarray) -> float:
    raise NotImplementedError


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    raise NotImplementedError


KERNEL_SIZE = {
    "type": "int",
    "min": 3,
    "max": 21,
    "step": 2,
    "default": 3,
    "label": "Kernel size (odd)",
}


class AverageFilter(ImageProcessor):
    name = "Average"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def _process(self, image, kernel_size, **_):
        raise NotImplementedError


class GaussianFilter(ImageProcessor):
    name = "Gaussian"
    params_schema = {
        "kernel_size": {**KERNEL_SIZE, "default": 5},
        "sigma": {
            "type": "float",
            "min": 0.1,
            "max": 10,
            "step": 0.1,
            "default": 1.0,
            "label": "Sigma",
        },
    }

    def _process(self, image, kernel_size, sigma, **_):
        """Kernel from G(x,y) = 1/(2*pi*sigma^2) * exp(-(x^2+y^2)/(2*sigma^2)), normalised to sum 1."""
        raise NotImplementedError


class MedianFilter(ImageProcessor):
    name = "Median"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def _process(self, image, kernel_size, **_):
        raise NotImplementedError


FILTERS = {c.name: c for c in (AverageFilter, GaussianFilter, MedianFilter)}
