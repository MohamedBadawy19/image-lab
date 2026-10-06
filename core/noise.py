"""Task 1 - additive noise. ALL FROM SCRATCH with np.random (no OpenCV)."""

import numpy as np

from core.base import ImageProcessor


class UniformNoise(ImageProcessor):
    name = "Uniform"
    params_schema = {
        "low": {"type": "int", "min": -100, "max": 0, "step": 1, "default": -30, "label": "Low"},
        "high": {"type": "int", "min": 0, "max": 100, "step": 1, "default": 30, "label": "High"},
    }

    def _process(self, image: np.ndarray, low, high, **_):
        raise NotImplementedError


class GaussianNoise(ImageProcessor):
    name = "Gaussian"
    params_schema = {
        "mean": {
            "type": "float",
            "min": -50,
            "max": 50,
            "step": 1,
            "default": 0,
            "label": "Mean",
        },
        "sigma": {
            "type": "float",
            "min": 1,
            "max": 100,
            "step": 1,
            "default": 25,
            "label": "Sigma",
        },
    }

    def _process(self, image: np.ndarray, mean, sigma, **_):
        raise NotImplementedError


class SaltPepperNoise(ImageProcessor):
    name = "Salt & Pepper"
    params_schema = {
        "amount": {
            "type": "float",
            "min": 0.01,
            "max": 0.5,
            "step": 0.01,
            "default": 0.05,
            "label": "Amount",
        },
        "salt_ratio": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
            "default": 0.5,
            "label": "Salt ratio",
        },
    }

    def _process(self, image: np.ndarray, amount, salt_ratio, **_):
        raise NotImplementedError


NOISES = {c.name: c for c in (UniformNoise, GaussianNoise, SaltPepperNoise)}
