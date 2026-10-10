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
    def __init__(self):
        super().__init__()
        self._cached_image = None
        self._cached_fft = None

    def _get_fft(self, image: np.ndarray):
        """Return cached FFT data for this image."""
        if self._cached_image is None or not np.array_equal(self._cached_image, image):
            self._cached_image = image.copy()  # Cache the image
            self._cached_fft = np.fft.fft2(image,axes=(0, 1))  # Compute FFT and cache it
        return self._cached_fft

    def spectrum(self, image: np.ndarray) -> np.ndarray:
        # 1. Calculate the 2D Fourier Transform
        fft_result = self._get_fft(image)

        # 2. Shift the zero frequency to the center
        shifted_fft = np.fft.fftshift(fft_result,axes=(0, 1))

        # 3. Calculate magnitude
        magnitude = np.abs(shifted_fft)

        # 4. Compress the dynamic range
        log_magnitude = np.log1p(magnitude)  # log(1 + magnitude)

        # 5. Normalize to [0, 255]
        min_val = np.min(log_magnitude)
        max_val = np.max(log_magnitude)

        if max_val > min_val:
            normalized = (log_magnitude - min_val) / (max_val - min_val) * 255
        else:
            normalized = np.zeros_like(log_magnitude)

        # 6. Convert to uint8
        return normalized.astype(np.uint8)

    def mask(self,shape: tuple,pass_type: str,mask_type: str,cutoff: int) -> np.ndarray:

        rows, cols = shape[:2]

        # 1. Find the center of the frequency domain
        center_y = rows // 2
        center_x = cols // 2

        # 2. Create coordinate grids
        y, x = np.ogrid[:rows, :cols]

        # 3. Calculate distance from the center
        distance = np.sqrt((y - center_y)**2 + (x - center_x)**2)

        # 4. Build the low-pass mask
        if mask_type == "ideal":
            low_mask = np.zeros((rows, cols))
            low_mask[distance <= cutoff] = 1.0
        elif mask_type == "gaussian":
            low_mask = np.exp(-(distance**2) / (2 * (cutoff**2)))

        else:
            raise ValueError("Invalid mask type")

        # 5. Return low-pass or high-pass
        if pass_type == "low":
            return low_mask

        elif pass_type == "high":
            return 1 - low_mask

        else:
            raise ValueError("Invalid pass type")

    def _reconstruct(self, fft_result: np.ndarray, pass_type: str, mask_type: str, cutoff: int) -> np.ndarray:
        # 1. Create the mask
        mask = self.mask(fft_result.shape, pass_type, mask_type, cutoff)

        if fft_result.ndim == 3:
            mask = mask[:, :, np.newaxis]      # 2. Apply the mask to the shifted FFT result
        shifted_fft = np.fft.fftshift(fft_result,axes=(0, 1))
        filtered_fft = shifted_fft * mask

        # 3. Shift back and compute the inverse FFT
        unshifted_fft = np.fft.ifftshift(filtered_fft,axes=(0, 1))
        reconstructed_image = np.fft.ifft2(unshifted_fft,axes=(0, 1))

        # 4. Return the real part of the reconstructed image
        return np.real(reconstructed_image)

    def _process(self, image, pass_type, mask_type, cutoff, **_):
        # Calculate or retrieve the FFT for the whole image
        fft_result = self._get_fft(image)

        # Reconstruct the filtered image
        return self._reconstruct(fft_result, pass_type, mask_type, cutoff)


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
