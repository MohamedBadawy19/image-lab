"""ImageData: load/save, cached gray conversion, channel split. Used by the whole app."""

from functools import cached_property
from pathlib import Path

import cv2
import numpy as np

from core.base import ImageLoadError, UnsupportedImageError

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


class ImageData:
    def __init__(self, array: np.ndarray, path: str | None = None):
        if not isinstance(array, np.ndarray) or array.size == 0:
            raise UnsupportedImageError("Invalid image data.")
        self.array = array
        self.path = path

    @classmethod
    def load(cls, path: str, as_gray: bool = False) -> "ImageData":
        """OpenCV is allowed here (task 1: read RGB and gray images)."""
        p = Path(path)
        if not p.exists():
            raise ImageLoadError(f"File not found: {p.name}")
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ImageLoadError(f"Unsupported file type '{p.suffix}'.")
        # np.fromfile + imdecode so Windows paths with non-ASCII characters work.
        data = np.fromfile(str(p), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE if as_gray else cv2.IMREAD_COLOR)
        if img is None:
            raise ImageLoadError(f"Could not read '{p.name}' (corrupt file?).")
        if not as_gray:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # the ONLY place channel order changes
        return cls(img, str(p))

    @classmethod
    def from_array(cls, array: np.ndarray, path: str | None = None) -> "ImageData":
        return cls(array, path)

    @staticmethod
    def save(path: str, image: np.ndarray) -> None:
        ext = Path(path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ImageLoadError(f"Unsupported file type '{ext}'.")
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.ndim == 3 else image
        ok, buf = cv2.imencode(ext, bgr)
        if not ok:
            raise ImageLoadError("Could not encode the image.")
        buf.tofile(path)

    @property
    def is_gray(self) -> bool:
        return self.array.ndim == 2

    @property
    def shape(self) -> tuple:
        return self.array.shape

    @property
    def channels(self) -> tuple:
        """(R, G, B) arrays, or (gray,) for a gray image."""
        if self.is_gray:
            return (self.array,)
        return tuple(self.array[..., i] for i in range(3))

    @cached_property
    def gray(self) -> np.ndarray:
        """FROM SCRATCH (task 8): 0.299 R + 0.587 G + 0.114 B. Cached: computed once per image."""
        if self.is_gray:
            return self.array
        weights = np.array([0.299, 0.587, 0.114])
        return np.clip(np.rint(self.array[..., :3].astype(np.float64) @ weights), 0, 255).astype(
            np.uint8
        )
