"""Task 3 - edge detection. direction: 'x' | 'y' | 'both'."""
import numpy as np


def sobel(img: np.ndarray, direction: str = "both") -> np.ndarray:
    raise NotImplementedError


def roberts(img: np.ndarray, direction: str = "both") -> np.ndarray:
    raise NotImplementedError


def prewitt(img: np.ndarray, direction: str = "both") -> np.ndarray:
    raise NotImplementedError


def canny(img: np.ndarray, low: int = 100, high: int = 200) -> np.ndarray:
    """OpenCV allowed (cv2.Canny) - only for task 1. No x/y preview."""
    raise NotImplementedError
