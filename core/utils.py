"""Shared image helpers. No dependency on the processor classes."""

import numpy as np


def pad(img, kh, kw, mode="constant"):
    # for even kernals, the result is positioned at the top left.
    # for odd, it's positioned at the center
    return np.pad(img, (((kh - 1) // 2, kh // 2), ((kw - 1) // 2, kw // 2)), mode=mode)


def sliding_window(image, kh, kw, fn, pad_mode="constant"):
    padded = pad(image, kh, kw, mode=pad_mode)
    output = np.zeros_like(image, dtype=np.float64)
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            output[i, j] = fn(padded[i:i + kh, j:j + kw])
    return output


def convolve(image, kernel):
    kh, kw = kernel.shape
    return sliding_window(image, kh, kw, lambda w: np.sum(w * kernel))


def mse(a, b):
    a = a.astype(np.float64)    # avoid uint8 wraparound and overflow when squaring
    b = b.astype(np.float64)
    return np.mean((a - b) ** 2)


def psnr(a, b):
    err = mse(a, b)
    if err == 0:
        return float("inf")
    return 10 * np.log10(255.0 ** 2 / err)


def to_uint8(img):
    return np.round(np.clip(img, 0, 255)).astype(np.uint8)


def to_gray(img):
    if img.ndim == 2:
        return img
    return img @ np.array([0.299, 0.587, 0.114])    # standard numbers for gray scale