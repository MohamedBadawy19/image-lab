"""Task 1 - additive noise. ALL FROM SCRATCH with np.random (no OpenCV)."""

import numpy as np

from core.base import ImageProcessor
import random



class UniformNoise(ImageProcessor):
    name = "Uniform"
    is_per_channel = False
    params_schema = {
        "low": {"type": "int", "min": -100, "max": 0, "step": 1, "default": -30, "label": "Low"},
        "high": {"type": "int", "min": 0, "max": 100, "step": 1, "default": 30, "label": "High"},
    }

    def _process(self, image: np.ndarray, low, high, **_):
        noisy = image + np.random.uniform(low, high, image.shape)
        return noisy


class GaussianNoise(ImageProcessor):
    name = "Gaussian"
    is_per_channel = False
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
        noisy = image + np.random.normal(mean, sigma, image.shape)
        return noisy


class SaltPepperNoise(ImageProcessor):
    name = "Salt & Pepper"
    is_per_channel = False
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
        image = image.copy()
        H = image.shape[0]      # rows      =>   y
        W = image.shape[1]      # colunms   =>   x
        N = int(amount *W * H)
        N_salt = int(N*salt_ratio)

        points = set()
        while len(points) < N:
            x = random.randint(0, W-1)
            y = random.randint(0, H-1)
            points.add((x, y))
        points = list(points)  
        random.shuffle(points)  # Must convert to list before shuffle
        
        salt_points = points[:N_salt]
        pepper_points = points[N_salt:]

        for x, y in salt_points:
            image[y, x] = 255     # row first, then column

        for x, y in pepper_points:
            image[y, x] = 0

        return image


NOISES = {c.name: c for c in (UniformNoise, GaussianNoise, SaltPepperNoise)}
