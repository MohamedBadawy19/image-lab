"""Feature catalog and unified execution engine for ImageLab Studio.

This module maps core processor dictionaries into a structured catalog for the GUI.
It provides a single execution point: run_feature(), ensuring that sidebar, analysis
panel, and main window remain completely generic.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from core.base import InvalidParameterError, UnsupportedImageError
from core.edges import EDGES, EdgeResult
from core.filters import FILTERS
from core.frequency import FREQ_FILTERS, FrequencyFilter, HybridBuilder, HybridResult
from core.histogram import HISTOGRAM_TOOLS
from core.image_data import ImageData
from core.noise import NOISES


@dataclass
class FeatureEntry:
    """Descriptor for a selectable feature in the Studio catalog."""

    id: str
    name: str
    group: str
    params_schema: dict
    needs_second_image: bool = False
    has_xy: bool = False
    processor_cls: Any = None


@dataclass
class FeatureOutput:
    """Unified result container returned by all feature runs."""

    result: np.ndarray
    extras: dict[str, np.ndarray] = field(default_factory=dict)


def _build_catalog() -> dict[str, list[FeatureEntry]]:
    """Build the catalog mapping group labels to lists of FeatureEntry."""
    catalog: dict[str, list[FeatureEntry]] = {}

    # 1. Noise
    noise_entries = []
    for name, cls in NOISES.items():
        noise_entries.append(
            FeatureEntry(
                id=f"noise_{cls.name.lower().replace(' ', '_')}",
                name=name,
                group="Noise",
                params_schema=cls.params_schema,
                processor_cls=cls,
            )
        )
    catalog["Noise"] = noise_entries

    # 2. Filters
    filter_entries = []
    for name, cls in FILTERS.items():
        filter_entries.append(
            FeatureEntry(
                id=f"filter_{cls.name.lower()}",
                name=name,
                group="Filters",
                params_schema=cls.params_schema,
                processor_cls=cls,
            )
        )
    catalog["Filters"] = filter_entries

    # 3. Edges
    edge_entries = []
    for name, cls in EDGES.items():
        edge_entries.append(
            FeatureEntry(
                id=f"edge_{cls.name.lower()}",
                name=name,
                group="Edges",
                params_schema=cls.params_schema,
                has_xy=getattr(cls, "has_xy", True),
                processor_cls=cls,
            )
        )
    catalog["Edges"] = edge_entries

    # 4. Histogram
    histo_entries = [
        FeatureEntry(
            id="hist_rgb_to_gray",
            name="RGB → Gray",
            group="Histogram",
            params_schema={},
        )
    ]
    for name, cls in HISTOGRAM_TOOLS.items():
        histo_entries.append(
            FeatureEntry(
                id=f"hist_{cls.name.lower()}",
                name=name,
                group="Histogram",
                params_schema=cls.params_schema,
                processor_cls=cls,
            )
        )
    catalog["Histogram"] = histo_entries

    # 5. Frequency
    freq_entries = []
    for name, cls in FREQ_FILTERS.items():
        freq_entries.append(
            FeatureEntry(
                id=f"freq_{cls.name.lower().replace(' ', '_')}",
                name=name,
                group="Frequency",
                params_schema=cls.params_schema,
                processor_cls=cls,
            )
        )
    catalog["Frequency"] = freq_entries

    # 6. Hybrid
    hybrid_schema = {
        "cutoff_low": {
            "type": "int",
            "min": 1,
            "max": 200,
            "step": 1,
            "default": 20,
            "label": "Cutoff A (Low-pass)",
        },
        "cutoff_high": {
            "type": "int",
            "min": 1,
            "max": 200,
            "step": 1,
            "default": 20,
            "label": "Cutoff B (High-pass)",
        },
    }
    catalog["Hybrid"] = [
        FeatureEntry(
            id="hybrid_builder",
            name="Hybrid Image",
            group="Hybrid",
            params_schema=hybrid_schema,
            needs_second_image=True,
            processor_cls=HybridBuilder,
        )
    ]

    return catalog


CATALOG = _build_catalog()


def run_feature(
    entry: FeatureEntry,
    image_data: ImageData,
    params: dict,
    second_image: ImageData | None = None,
) -> FeatureOutput:
    """Run any feature uniformly and return a FeatureOutput."""
    if image_data is None:
        raise UnsupportedImageError("No valid image to process. Open an image first.")

    # Special case: RGB -> Gray conversion
    if entry.id == "hist_rgb_to_gray":
        if image_data.is_gray:
            raise UnsupportedImageError("Image is already gray.")
        return FeatureOutput(result=image_data.gray)

    # Special case: Hybrid image builder
    if entry.group == "Hybrid":
        if second_image is None:
            raise InvalidParameterError("Load a second image first.")
        cutoff_low = params.get("cutoff_low", 20)
        cutoff_high = params.get("cutoff_high", 20)
        hybrid_res: HybridResult = HybridBuilder.build(
            image_data.array,
            second_image.array,
            cutoff_low=cutoff_low,
            cutoff_high=cutoff_high,
        )
        return FeatureOutput(
            result=hybrid_res.hybrid,
            extras={"low": hybrid_res.low, "high": hybrid_res.high},
        )

    # Special case: Edge detection
    if entry.group == "Edges":
        detector = entry.processor_cls()
        edge_res: EdgeResult = detector.detect(image_data.gray, **params)
        extras = {}
        if entry.has_xy and edge_res.gx is not None and edge_res.gy is not None:
            extras["gx"] = edge_res.gx
            extras["gy"] = edge_res.gy
        return FeatureOutput(result=edge_res.magnitude, extras=extras)

    # Special case: Frequency domain filter
    if entry.group == "Frequency":
        proc: FrequencyFilter = entry.processor_cls()
        res = proc.apply(image_data.array, **params)
        shape = image_data.array.shape[:2]
        pass_type = params.get("pass_type", "low")
        mask_type = params.get("mask_type", "gaussian")
        cutoff = params.get("cutoff", 30)
        mask = proc.mask(shape, pass_type, mask_type, cutoff)
        mask_display = (np.clip(mask, 0, 1) * 255).astype(np.uint8)
        return FeatureOutput(result=res, extras={"mask": mask_display})

    # General case: ImageProcessor subclass (Noise, Filters, Histogram tools)
    processor = entry.processor_cls()
    res = processor.apply(image_data.array, **params)
    return FeatureOutput(result=res)
