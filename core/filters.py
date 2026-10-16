"""Task 2 - low pass filters, FROM SCRATCH."""

from abc import abstractmethod

import numpy as np
from scipy import ndimage

from core.base import ImageProcessor
from core.convolution import convolve
from core.utils import timed


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

    # algorithm used for the convolution: "naive" | "optimized" | "scipy"
    method = "scipy"

    @abstractmethod    # every subclass must implement
    def build_kernel(self, **params):
        ...

    def _process(self, image, **params):
        return convolve(image, self.build_kernel(**params), method=self.method)


class AverageFilter(KernelFilter):
    name = "Average"
    method = "naive"    # change to "naive" or "scipy" to compare
    params_schema = {"kernel_size": KERNEL_SIZE}

    def build_kernel(self, kernel_size, **_):
        return np.ones((kernel_size, kernel_size), dtype=np.float64) / kernel_size ** 2


class GaussianFilter(KernelFilter):
    name = "Gaussian"
    method = "scipy"
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



@timed
def median_scipy(image, k):
    # median is not a convolution, so it only has the scipy implementation
    return ndimage.median_filter(image.astype(np.float64, copy=False), size=k, mode="nearest")


# Median filter is only applied with scipy
class MedianFilter(ImageProcessor):
    name = "Median"
    method = "scipy"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def _process(self, image, kernel_size, **_):
        return median_scipy(image, kernel_size)


FILTERS = {c.name: c for c in (AverageFilter, GaussianFilter, MedianFilter)}