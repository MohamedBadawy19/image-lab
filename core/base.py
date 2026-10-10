"""Shared contracts for the whole team: exceptions + ImageProcessor base class."""

from abc import ABC, abstractmethod

import numpy as np

from core.utils import to_uint8


class AppError(Exception):
    """Base of all expected errors. str(error) is shown to the user."""


class ImageLoadError(AppError):
    """File missing, corrupt or unsupported."""


class InvalidParameterError(AppError):
    """A parameter is out of range (even kernel size, sigma <= 0, ...)."""


class UnsupportedImageError(AppError):
    """Wrong image for this operation (no image, wrong channels, ...)."""


class ProcessingError(AppError):
    """Anything that fails during processing."""


class ImageProcessor(ABC):
    """Template Method: apply() = defaults -> validate -> float -> _process -> _finalize.

    params_schema example:
        {"sigma": {"type": "float", "min": 0.1, "max": 10, "step": 0.1, "default": 1.0, "label": "Sigma"},
         "size":  {"type": "int", "min": 3, "max": 21, "step": 2, "default": 3, "odd": True},
         "mode":  {"type": "select", "options": ["low", "high"], "default": "low"}}
    type is "int" | "float" | "select". The GUI builds its controls from this schema.

    handles_color:
        False -> an RGB image is split into channels and _process gets each 2D channel.
        True  -> _process gets the full array (edge detectors, equalizer, ...).
    """

    name: str = ""
    params_schema: dict = {}
    handles_color: bool = False

    def apply(self, image: np.ndarray, **params):
        params = self._with_defaults(params)
        self._validate(image, **params)
        return self._finalize(self._run(image.astype(np.float64), **params))

    def _run(self, data, **params):
        if data.ndim == 3 and not self.handles_color:
            channels = [self._process(data[..., c], **params) for c in range(data.shape[2])]
            return np.stack(channels, axis=-1)
        return self._process(data, **params)

    def _with_defaults(self, params: dict) -> dict:
        merged = {k: v["default"] for k, v in self.params_schema.items() if "default" in v}
        merged.update(params)
        return merged

    def _validate(self, image, **params) -> None:
        if not isinstance(image, np.ndarray) or image.size == 0:
            raise UnsupportedImageError("No valid image to process. Open an image first.")
        if image.ndim not in (2, 3) or (image.ndim == 3 and image.shape[2] != 3):
            raise UnsupportedImageError("Image must be grayscale or 3-channel RGB.")
        for key, spec in self.params_schema.items():
            value = params.get(key)
            if value is None:
                continue
            if "min" in spec and value < spec["min"]:
                raise InvalidParameterError(f"{key} must be >= {spec['min']} (got {value}).")
            if "max" in spec and value > spec["max"]:
                raise InvalidParameterError(f"{key} must be <= {spec['max']} (got {value}).")
            if spec.get("odd") and int(value) % 2 == 0:
                raise InvalidParameterError(f"{key} must be odd (got {value}).")
            if spec.get("options") and value not in spec["options"]:
                raise InvalidParameterError(f"{key} must be one of {spec['options']}.")

    @abstractmethod
    def _process(self, image: np.ndarray, **params):
        """Subclasses implement ONLY this step."""

    def _finalize(self, out):
        return to_uint8(out)