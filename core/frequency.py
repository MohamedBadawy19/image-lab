"""Task 9 - frequency domain filters. numpy.fft allowed."""
import numpy as np


def fft_spectrum(img: np.ndarray) -> np.ndarray:
    """log(1+|fftshift(fft2)|) scaled to uint8 - shown in the Analysis window."""
    raise NotImplementedError


def lowpass_filter(img: np.ndarray, cutoff: int = 30, kind: str = "gaussian") -> np.ndarray:
    """kind: 'ideal' | 'gaussian' | 'butterworth'."""
    raise NotImplementedError


def highpass_filter(img: np.ndarray, cutoff: int = 30, kind: str = "gaussian") -> np.ndarray:
    raise NotImplementedError
