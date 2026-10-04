"""Image I/O helpers. OpenCV allowed here."""
import base64
import cv2
import numpy as np


def decode_image(file_bytes: bytes, gray: bool = False) -> np.ndarray:
    """Bytes (uploaded file) -> uint8 array. Returns RGB (H,W,3) or gray (H,W)."""
    raise NotImplementedError


def encode_png_b64(img: np.ndarray) -> str:
    """uint8 array -> 'data:image/png;base64,...' string for the browser."""
    raise NotImplementedError


def to_uint8(img: np.ndarray) -> np.ndarray:
    """Clip to [0,255] and cast to uint8 (use after every filter)."""
    raise NotImplementedError


def is_gray(img: np.ndarray) -> bool:
    return img.ndim == 2
