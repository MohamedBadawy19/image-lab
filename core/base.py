"""Shared contracts for the whole team: exceptions + ImageProcessor base class."""

from abc import ABC, abstractmethod

import numpy as np


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
    """Template Method: apply() = fill defaults -> validate -> _process -> _finalize.

    params_schema example:
        {"sigma": {"type": "float", "min": 0.1, "max": 10, "step": 0.1, "default": 1.0, "label": "Sigma"},
         "mode":  {"type": "select", "options": ["low", "high"], "default": "low"}}
    type is "int" | "float" | "select". The GUI builds its controls from this schema.
    """

    name: str = ""
    params_schema: dict = {}

    def apply(self, image: np.ndarray, **params):
        params = self._with_defaults(params)
        self._validate(image, **params)
        return self._finalize(self._process(image, **params))

    def _with_defaults(self, params: dict) -> dict:
        merged = {k: v["default"] for k, v in self.params_schema.items() if "default" in v}
        merged.update(params)
        return merged

    def _validate(self, image, **params) -> None:
        if not isinstance(image, np.ndarray) or image.size == 0:
            raise UnsupportedImageError("No valid image to process. Open an image first.")
        for key, spec in self.params_schema.items():
            value = params.get(key)
            if value is None:
                continue
            if "min" in spec and value < spec["min"]:
                raise InvalidParameterError(f"{key} must be >= {spec['min']} (got {value}).")
            if "max" in spec and value > spec["max"]:
                raise InvalidParameterError(f"{key} must be <= {spec['max']} (got {value}).")
            if spec.get("options") and value not in spec["options"]:
                raise InvalidParameterError(f"{key} must be one of {spec['options']}.")

    @abstractmethod
    def _process(self, image: np.ndarray, **params):
        """Subclasses implement ONLY this step."""

    def _finalize(self, out):
        return np.clip(out, 0, 255).astype(np.uint8)
