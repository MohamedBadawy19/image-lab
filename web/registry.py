"""Single source of truth for the UI.
The frontend calls GET /api/features and BUILDS the sidebar + sliders from this.
To add a feature: write fn in core/, add one entry here. No JS change needed.

param types: 'int' | 'float' | 'select'.   output: 'image'.
second_image=True -> UI shows a 2nd upload slot (hybrid).
"""
from core import noise, filters, edges, equalize, normalize, color, frequency, hybrid

DIRS = {"name": "direction", "type": "select", "options": ["both", "x", "y"], "default": "both"}
KS = lambda d=3: {"name": "ksize", "type": "int", "min": 3, "max": 21, "step": 2, "default": d}
KINDS = {"name": "kind", "type": "select", "options": ["ideal", "gaussian", "butterworth"], "default": "gaussian"}
CUT = lambda: {"name": "cutoff", "type": "int", "min": 1, "max": 200, "step": 1, "default": 30}

FEATURES = {
    # ---- Noise
    "gaussian_noise": {"group": "Noise", "label": "Gaussian noise", "fn": noise.add_gaussian_noise,
        "params": [{"name": "mean", "type": "float", "min": -50, "max": 50, "step": 1, "default": 0},
                   {"name": "sigma", "type": "float", "min": 1, "max": 100, "step": 1, "default": 25}]},
    "salt_pepper": {"group": "Noise", "label": "Salt & pepper", "fn": noise.add_salt_pepper_noise,
        "params": [{"name": "amount", "type": "float", "min": 0.01, "max": 0.5, "step": 0.01, "default": 0.05},
                   {"name": "salt_ratio", "type": "float", "min": 0, "max": 1, "step": 0.05, "default": 0.5}]},
    # ---- Filters
    "average": {"group": "Filters", "label": "Average", "fn": filters.average_filter, "params": [KS()]},
    "gaussian": {"group": "Filters", "label": "Gaussian", "fn": filters.gaussian_filter,
        "params": [KS(5), {"name": "sigma", "type": "float", "min": 0.1, "max": 10, "step": 0.1, "default": 1.0}]},
    "median": {"group": "Filters", "label": "Median", "fn": filters.median_filter, "params": [KS()]},
    # ---- Edges
    "sobel": {"group": "Edges", "label": "Sobel", "fn": edges.sobel, "params": [DIRS]},
    "roberts": {"group": "Edges", "label": "Roberts", "fn": edges.roberts, "params": [DIRS]},
    "prewitt": {"group": "Edges", "label": "Prewitt", "fn": edges.prewitt, "params": [DIRS]},
    "canny": {"group": "Edges", "label": "Canny (OpenCV)", "fn": edges.canny,
        "params": [{"name": "low", "type": "int", "min": 0, "max": 255, "step": 1, "default": 100},
                   {"name": "high", "type": "int", "min": 0, "max": 255, "step": 1, "default": 200}]},
    # ---- Histogram tools
    "equalize": {"group": "Histogram", "label": "Equalize", "fn": equalize.equalize, "params": []},
    "normalize": {"group": "Histogram", "label": "Normalize", "fn": normalize.normalize,
        "params": [{"name": "new_min", "type": "int", "min": 0, "max": 254, "step": 1, "default": 0},
                   {"name": "new_max", "type": "int", "min": 1, "max": 255, "step": 1, "default": 255}]},
    "to_gray": {"group": "Histogram", "label": "RGB -> Gray", "fn": color.rgb_to_gray, "params": []},
    # ---- Frequency
    "freq_lowpass": {"group": "Frequency", "label": "Low pass", "fn": frequency.lowpass_filter, "params": [CUT(), KINDS]},
    "freq_highpass": {"group": "Frequency", "label": "High pass", "fn": frequency.highpass_filter, "params": [CUT(), KINDS]},
    # ---- Hybrid
    "hybrid": {"group": "Hybrid", "label": "Hybrid image", "fn": hybrid.hybrid_image, "second_image": True,
        "params": [{"name": "cutoff_low", "type": "int", "min": 1, "max": 100, "step": 1, "default": 20},
                   {"name": "cutoff_high", "type": "int", "min": 1, "max": 100, "step": 1, "default": 20}]},
}
