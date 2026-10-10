"""Task 2 - low pass filters, FROM SCRATCH."""

from abc import abstractmethod

import numpy as np

from core.base import ImageProcessor
from core.utils import convolve, sliding_window


KERNEL_SIZE = {
    "type": "int",
    "min": 3,
    "max": 21,
    "step": 2,
    "default": 3,
    "odd": True,
    "label": "Kernel size (odd)",   
}


class KernelFilter(ImageProcessor):
    """Linear filters: subclasses only build the kernel."""

    @abstractmethod    # every subclass must implement
    def build_kernel(self, **params):
        ...

    def _process(self, image, **params):
        return convolve(image, self.build_kernel(**params))


class AverageFilter(KernelFilter):
    name = "Average"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def build_kernel(self, kernel_size, **_):
        return np.ones((kernel_size, kernel_size), dtype=np.float64) / kernel_size ** 2


class GaussianFilter(KernelFilter):
    name = "Gaussian"
    params_schema = {
        "kernel_size": {**KERNEL_SIZE, "default": 5},
        "sigma": {"type": "float", "min": 0.1, "max": 10, "step": 0.1, "default": 1.0, "label": "Sigma"},
    }

    def build_kernel(self, kernel_size, sigma, **_):
        """G(x,y) = 1/(2*pi*sigma^2) * exp(-(x^2+y^2)/(2*sigma^2)), normalised to sum 1."""
        r = kernel_size // 2
        ax = np.arange(-r, r + 1)
        x, y = np.meshgrid(ax, ax)
        k = 1 / (2 * np.pi * sigma ** 2) * np.exp(-(x ** 2 + y ** 2) / (2 * sigma ** 2))
        return k / k.sum()


class MedianFilter(ImageProcessor):
    name = "Median"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def _process(self, image, kernel_size, **_):
        return sliding_window(image, kernel_size, kernel_size, np.median, pad_mode="edge")


FILTERS = {c.name: c for c in (AverageFilter, GaussianFilter, MedianFilter)}