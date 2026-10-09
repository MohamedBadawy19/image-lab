"""Task 2 - low pass filters, FROM SCRATCH. convolve() is shared by filters AND edge detectors."""

import numpy as np

from core.base import ImageProcessor


KERNEL_SIZE = {
    "type": "int",
    "min": 3,
    "max": 21,
    "step": 2,
    "default": 3,
    "label": "Kernel size (odd)",
}

def convolve(image, kernel):
    kh, kw = kernel.shape
    padded = pad(image, kh, kw)
    output = np.zeros_like(image, dtype=np.float64)
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            output[i, j] = np.sum(padded[i:i+kh, j:j+kw] * kernel)
    return output

def pad(img, kh, kw):
    # ph: increase height,   pw: increase width
    ph, pw = (kh - 1)//2, (kw - 1)//2
    padded = np.pad(img, ((ph, ph), (pw, pw)), "constant")
    return padded


def mse(a, b) :
    a = a.astype(np.float64)    # avoid uint8 wraparound (5 - 10 = 251) and overflow when squaring
    b = b.astype(np.float64)
    return np.mean((a - b)**2)


def psnr(a, b):
    err = mse(a,b)
    if err == 0:
        return float("inf")
    return 10 * np.log10(255.0 ** 2 / err)  # 255 for non-normalized images




class AverageFilter(ImageProcessor):
    name = "Average"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def _process(self, image, kernel_size, **_):
        
        return cov



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
