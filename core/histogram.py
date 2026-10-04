"""Task 4 + 8 - histogram, distribution curve (PDF), cumulative curve (CDF)."""
import numpy as np


def compute_histogram(channel: np.ndarray) -> np.ndarray:
    """256-bin counts for ONE channel, from scratch (no np.histogram)."""
    raise NotImplementedError


def compute_cdf(hist: np.ndarray) -> np.ndarray:
    """Cumulative distribution, normalised to [0,1]."""
    raise NotImplementedError


def analyze(img: np.ndarray) -> dict:
    """What the Analysis window needs:
    gray -> {'channels': {'gray': {'hist': [...], 'cdf': [...]}}}
    rgb  -> {'channels': {'r': {...}, 'g': {...}, 'b': {...}}}
    """
    raise NotImplementedError
