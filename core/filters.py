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

def pad(img, kh, kw, mode = "constant"):
    # ph: increase height,   pw: increase width
    ph, pw = (kh - 1)//2, (kw - 1)//2
    padded = np.pad(img, ((ph, ph), (pw, pw)), mode = mode)
    return padded

def sliding_window(image, kh, kw, fn, pad_mode = "constant"):
    padded = pad(image, kh, kw, mode = pad_mode)
    output = np.zeros_like(image, dtype=np.float64)
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            output[i, j] = fn(padded[i:i+kh, j:j+kw])
    return output

def convolve(image, kernel):
    kh, kw = kernel.shape
    fn = lambda w: np.sum(w * kernel)
    return sliding_window(image, kh, kw, fn)


def mse(a, b) :
    a = a.astype(np.float64)    # avoid uint8 wraparound (5 - 10 = 251) and overflow when squaring
    b = b.astype(np.float64)
    return np.mean((a - b)**2)


def psnr(a, b):
    err = mse(a,b)
    if err == 0:
        return float("inf")
    return 10 * np.log10(255.0 ** 2 / err)  # 255 for non-normalized images


def to_uint8(img):
    clipped = np.clip(img, 0, 255)
    return np.round(clipped).astype(np.uint8)

class AverageFilter(ImageProcessor):
    name = "Average"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def average_kernel(self, size):
        N = size * size
        return 1/N * np.ones((size, size), dtype=np.float64)

    def _process(self, image, kernel_size, **_):
        output = convolve(image, self.average_kernel(kernel_size))
        return to_uint8(output)



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

    def gaussian_kernel(self, size, sigma):
        """Kernel from G(x,y) = 1/(2*pi*sigma^2) * exp(-(x^2+y^2)/(2*sigma^2)), normalised to sum 1."""
        r = size // 2
        ax = np.arange(-r, r+1)
        x, y = np.meshgrid(ax, ax)
        k = 1/(2 * np.pi * sigma**2) * np.exp(-(x**2 + y**2) / (2 * sigma**2))
        return k / k.sum()

    def _process(self, image, kernel_size, sigma, **_):
        output = convolve(image, self.gaussian_kernel(kernel_size, sigma))
        return to_uint8(output)



class MedianFilter(ImageProcessor):
    name = "Median"
    params_schema = {"kernel_size": KERNEL_SIZE}

    def _process(self, image, kernel_size, **_):
        output = sliding_window(image, kernel_size, kernel_size, np.median, pad_mode = "edge")
        return to_uint8(output)


FILTERS = {c.name: c for c in (AverageFilter, GaussianFilter, MedianFilter)}
