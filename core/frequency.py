"""Tasks 9, 10 - frequency domain filters and hybrid images. numpy.fft is allowed."""

from dataclasses import dataclass

import numpy as np

from core.base import ImageProcessor


class FrequencyFilter(ImageProcessor):
    name = "Frequency filter"
    params_schema = {
        "pass_type": {
            "type": "select",
            "options": ["low", "high"],
            "default": "low",
            "label": "Pass",
        },
        "mask_type": {
            "type": "select",
            "options": ["ideal", "gaussian"],
            "default": "gaussian",
            "label": "Mask",
        },
        "cutoff": {
            "type": "int",
            "min": 1,
            "max": 200,
            "step": 1,
            "default": 30,
            "label": "Cutoff radius",
        },
    }

    def spectrum(self, image: np.ndarray) -> np.ndarray:
        """log(1 + |fftshift(fft2)|) scaled to uint8 for display. FFT cached per image."""
        raise NotImplementedError

    def mask(self, shape: tuple, pass_type: str, mask_type: str, cutoff: int) -> np.ndarray:
        """Float mask 0..1 for display. High pass = 1 - low pass (same function)."""
        raise NotImplementedError

    def _process(self, image, pass_type, mask_type, cutoff, **_):
        """fft2 -> fftshift -> multiply mask -> ifftshift -> ifft2. RGB per channel.
        Compute the FFT once per image and reuse it when only the cutoff changes."""
        raise NotImplementedError


@dataclass
class HybridResult:
    low: np.ndarray  # low-pass of image A
    high: np.ndarray  # high-pass of image B
    hybrid: np.ndarray  # low + high


class HybridBuilder:
    @staticmethod
    def build(
        image_a: np.ndarray,
        image_b: np.ndarray,
        cutoff_low: int = 20,
        cutoff_high: int = 20,
    ) -> HybridResult:
        """Resize B to A's shape (raise InvalidParameterError if impossible).
        Reuse FrequencyFilter masks."""
        raise NotImplementedError


FREQ_FILTERS = {FrequencyFilter.name: FrequencyFilter}
