"""Task 1 - additive noise."""
import numpy as np


def add_gaussian_noise(img: np.ndarray, mean: float = 0, sigma: float = 25) -> np.ndarray:
    """OpenCV allowed (cv2.randn). Add Gaussian noise, clip, return uint8."""
    raise NotImplementedError


def add_salt_pepper_noise(img: np.ndarray, amount: float = 0.05, salt_ratio: float = 0.5) -> np.ndarray:
    """FROM SCRATCH (numpy random mask). amount = fraction of pixels corrupted."""
    raise NotImplementedError
