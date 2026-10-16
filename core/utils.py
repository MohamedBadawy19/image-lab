"""Shared image helpers. No dependency on the processor classes."""

import time
import numpy as np

from functools import wraps

def timed(fn):
    # Decorator that prints how long each call to fn takes
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        shapes = ", ".join(str(a.shape) for a in args if hasattr(a, "shape"))
        print(f"{fn.__name__}({shapes}) took {elapsed:.4f} s")
        return result
    return wrapper


def pad(img, kh, kw, mode="constant"):
    # for even kernals, the result is positioned at the top left.
    # for odd, it's positioned at the center
    return np.pad(img, (((kh - 1) // 2, kh // 2), ((kw - 1) // 2, kw // 2)), mode=mode)


# ------------------------------------------------------------------- metrics
def mse(a, b):
    a = to_float(a)    # avoid uint8 wraparound and overflow when squaring
    b = to_float(b)
    return np.mean((a - b) ** 2)


# def psnr(a, b):
#     err = mse(a, b)
#     if err == 0:
#         return float("inf")
#     return 10 * np.log10(255.0 ** 2 / err)


def to_float(img):
    return img.astype(np.float64, copy=False)

def to_uint8(img):
    return np.round(np.clip(img, 0, 255)).astype(np.uint8)


def to_gray(img):
    if img.ndim == 2:
        return img
    return img @ np.array([0.299, 0.587, 0.114])    # standard numbers for gray scale