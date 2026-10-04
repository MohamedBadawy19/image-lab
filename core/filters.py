"""Task 2 - low pass filters (all from scratch)."""
import numpy as np


def convolve2d(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Shared convolution (pad + slide). Must support gray and RGB (per channel)."""
    raise NotImplementedError


def average_filter(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    raise NotImplementedError


def gaussian_kernel(ksize: int = 5, sigma: float = 1.0) -> np.ndarray:
    """Build the kernel from the Gaussian equation, normalised to sum 1."""
    raise NotImplementedError


def gaussian_filter(img: np.ndarray, ksize: int = 5, sigma: float = 1.0) -> np.ndarray:
    raise NotImplementedError


def median_filter(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Not a kernel - sort the window and take the median."""
    raise NotImplementedError
