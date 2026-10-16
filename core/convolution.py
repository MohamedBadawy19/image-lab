"""Convolution (correlation) algorithms: naive, optimized (manual) and scipy."""

import numpy as np
from scipy import ndimage

from core.utils import timed, pad, to_float


METHODS = ("naive", "optimized", "scipy")


def sliding_window(image, kh, kw, fn, pad_mode="constant"):
    padded = pad(image, kh, kw, mode=pad_mode)
    output = np.zeros_like(image, dtype=np.float64)
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            output[i, j] = fn(padded[i:i + kh, j:j + kw])
    return output

@timed
def convolve_naive(image, kernel):
    # python loop over every pixel: slowest, our own implementation
    kh, kw = kernel.shape
    return sliding_window(image, kh, kw, lambda w: np.sum(w * kernel))


def _separable_factors(kernel):
    # If kernel == outer(col, row) (rank 1) return (col, row), else None.
    # Average and Gaussian kernels are separable.
    idx = np.unravel_index(np.argmax(np.abs(kernel)), kernel.shape)
    pivot = kernel[idx]
    if pivot == 0:
        return None
    col = kernel[:, idx[1]]
    row = kernel[idx[0], :] / pivot
    if np.allclose(np.outer(col, row), kernel):
        return col, row
    return None

@timed
def convolve_optimized(image, kernel):
    # Manual optimization, no library convolution:
    #  - loop over kernel elements (kh*kw) instead of over pixels (H*W);
    #    each step multiplies the whole shifted image by one kernel value.
    #  - if the kernel is separable: two 1D passes -> O(H*W*(kh+kw)).
    kh, kw = kernel.shape
    h, w = image.shape
    padded = pad(image, kh, kw)
    factors = _separable_factors(kernel)

    if factors is not None:
        col, row = factors
        tmp = np.zeros((h + kh - 1, w), dtype=np.float64)    # horizontal pass
        for b in range(kw):
            tmp += row[b] * padded[:, b:b + w]
        out = np.zeros((h, w), dtype=np.float64)             # vertical pass
        for a in range(kh):
            out += col[a] * tmp[a:a + h]
        return out

    out = np.zeros((h, w), dtype=np.float64)
    for a in range(kh):
        for b in range(kw):
            out += kernel[a, b] * padded[a:a + h, b:b + w]
    return out


@timed
def convolve_scipy(image, kernel):
    assert kernel.shape[0] == kernel.shape[1], "kernel must be square"

    # 0 for odd kernels, -1 for even kernels (to match pad() alignment)
    origin = 0 if kernel.shape[0] % 2 == 1 else -1
    
    # float64 is needed: ndimage keeps the input dtype (uint8 would clip)
    return ndimage.correlate(
        to_float(image), kernel, mode="constant", cval=0.0, origin=origin
    )



_CONVOLVE = {"naive": convolve_naive, "optimized": convolve_optimized, "scipy": convolve_scipy}


def convolve(image, kernel, method="scipy"):
    if method not in _CONVOLVE:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    return _CONVOLVE[method](image, kernel)