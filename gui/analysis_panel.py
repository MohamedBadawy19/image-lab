"""Analysis Window — inner tabbed views for image statistics and frequency analysis.

Tabs:
1. Histogram: per-channel histogram & PDF with an Original vs Result overlay switch.
2. CDF: per-channel cumulative distribution curves.
3. Spectrum: log-magnitude Fourier spectrum display.
4. Details: feature extras (frequency filter mask, hybrid low/high components).

Data is computed ONCE per image/result change and cached. Any NotImplementedError
raised during analysis is quietly shown as a placeholder inside the view.
"""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.frequency import FrequencyFilter
from core.histogram import HistogramAnalyzer, HistogramResult
from core.image_data import ImageData
from gui.widgets import ImageViewer, PlotCanvas


class AnalysisPanel(QWidget):
    """Right-side Analysis window with inner tabs for Histogram, CDF, Spectrum, and Details."""

    _CHANNEL_COLORS = {
        "R": "#ef4444",
        "G": "#22c55e",
        "B": "#3b82f6",
        "Gray": "#cdd6f4",
    }
    _OVERLAY_COLORS = {
        "R": "#f97316",
        "G": "#10b981",
        "B": "#06b6d4",
        "Gray": "#facc15",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._orig_data: ImageData | None = None
        self._result_array: np.ndarray | None = None
        self._extras: dict[str, np.ndarray] = {}

        # Cached analysis calculations
        self._orig_analysis: list[HistogramResult] | None = None
        self._result_analysis: list[HistogramResult] | None = None

        self._freq_filter = FrequencyFilter()

        # Layout & Inner Tab Widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # 1. Histogram Tab
        self._setup_histogram_tab()

        # 2. CDF Tab
        self._setup_cdf_tab()

        # 3. Spectrum Tab
        self._setup_spectrum_tab()

        # 4. Details Tab
        self._setup_details_tab()

    # ------------------------------------------------------------------ Tab Setups

    def _setup_histogram_tab(self) -> None:
        """Create the Histogram & PDF analysis tab with overlay toggle."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        # Overlay checkbox
        top_row = QHBoxLayout()
        self._overlay_check = QCheckBox("Overlay Result on Original")
        self._overlay_check.setChecked(False)
        self._overlay_check.toggled.connect(self._render_histogram)
        top_row.addWidget(self._overlay_check)
        top_row.addStretch()
        layout.addLayout(top_row)

        self._hist_plot = PlotCanvas(width=5, height=3)
        self._hist_placeholder = QLabel("Open an image to view histogram")
        self._hist_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hist_placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")

        layout.addWidget(self._hist_plot)
        layout.addWidget(self._hist_placeholder)
        self._hist_placeholder.hide()

        self._tabs.addTab(widget, "📊 Histogram")

    def _setup_cdf_tab(self) -> None:
        """Create the CDF cumulative distribution curve tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self._cdf_plot = PlotCanvas(width=5, height=3)
        self._cdf_placeholder = QLabel("Open an image to view CDF")
        self._cdf_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cdf_placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")

        layout.addWidget(self._cdf_plot)
        layout.addWidget(self._cdf_placeholder)
        self._cdf_placeholder.hide()

        self._tabs.addTab(widget, "📈 CDF")

    def _setup_spectrum_tab(self) -> None:
        """Create the Fourier Spectrum viewer tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self._spectrum_viewer = ImageViewer("Fourier Spectrum (log magnitude)")
        self._spectrum_placeholder = QLabel("Fourier spectrum not available yet")
        self._spectrum_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spectrum_placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")

        layout.addWidget(self._spectrum_viewer)
        layout.addWidget(self._spectrum_placeholder)
        self._spectrum_placeholder.hide()

        self._tabs.addTab(widget, "🌐 Spectrum")

    def _setup_details_tab(self) -> None:
        """Create the Details tab for feature-specific extras."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self._details_splitter = QSplitter(Qt.Orientation.Vertical)
        self._detail_viewer1 = ImageViewer("Extra 1")
        self._detail_viewer2 = ImageViewer("Extra 2")
        self._details_splitter.addWidget(self._detail_viewer1)
        self._details_splitter.addWidget(self._detail_viewer2)

        self._details_placeholder = QLabel("No feature-specific details for current selection")
        self._details_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._details_placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")

        layout.addWidget(self._details_splitter)
        layout.addWidget(self._details_placeholder)

        self._tabs.addTab(widget, "🔍 Details")

    # ------------------------------------------------------------------ Public API

    def set_original(self, image_data: ImageData | None) -> None:
        """Called when the original working image changes."""
        self._orig_data = image_data
        self._orig_analysis = (
            self._compute_histogram_analysis(image_data.array) if image_data else None
        )
        self._result_array = None
        self._result_analysis = None
        self._extras = {}
        self._update_all()

    def set_result(
        self, result: np.ndarray | None, extras: dict[str, np.ndarray] | None = None
    ) -> None:
        """Called when a feature produces a new result or extras."""
        self._result_array = result
        self._result_analysis = (
            self._compute_histogram_analysis(result) if result is not None else None
        )
        self._extras = extras or {}
        self._update_all()

    def clear(self) -> None:
        """Clear all analysis data."""
        self._orig_data = None
        self._result_array = None
        self._orig_analysis = None
        self._result_analysis = None
        self._extras = {}
        self._update_all()

    # ------------------------------------------------------------------ Analysis & Rendering

    def _update_all(self) -> None:
        """Refresh all inner tabs with currently cached analysis."""
        self._render_histogram()
        self._render_cdf()
        self._render_spectrum()
        self._render_details()

    def _compute_histogram_analysis(self, image: np.ndarray) -> list[HistogramResult] | None:
        """Compute HistogramAnalyzer.analyze once per channel. Returns None on NotImplementedError."""
        try:
            if image.ndim == 2:
                channels = [image]
            else:
                channels = [image[..., i] for i in range(3)]
            results = []
            for ch in channels:
                res = HistogramAnalyzer.analyze(ch)
                results.append(res)
            return results
        except NotImplementedError:
            return None
        except Exception:
            return None

    def _render_histogram(self) -> None:
        """Plot per-channel Histogram & PDF with optional Original/Result overlay."""
        # Check if original is available
        if self._orig_data is None:
            self._hist_plot.hide()
            self._hist_placeholder.setText("Open an image to view histogram")
            self._hist_placeholder.show()
            return

        if self._orig_analysis is None:
            self._hist_plot.hide()
            self._hist_placeholder.setText("Histogram analysis not available yet (stub)")
            self._hist_placeholder.show()
            return

        self._hist_placeholder.hide()
        self._hist_plot.show()

        target_analysis = (
            self._result_analysis
            if (self._result_analysis is not None and not self._overlay_check.isChecked())
            else self._orig_analysis
        )
        is_gray = (
            (self._result_array.ndim == 2)
            if (self._result_array is not None and not self._overlay_check.isChecked())
            else self._orig_data.is_gray
        )
        n_channels = len(target_analysis)
        labels = ["Gray"] if is_gray else ["R", "G", "B"]

        try:
            axes = self._hist_plot.subplots(2, n_channels)
            if n_channels == 1:
                axes = axes.reshape(2, 1)

            for i, (analysis, lbl) in enumerate(zip(target_analysis, labels)):
                color = self._CHANNEL_COLORS[lbl]
                # Row 0: Histogram
                ax_h = axes[0, i]
                ax_h.bar(
                    range(256),
                    analysis.hist,
                    color=color,
                    alpha=0.6,
                    width=1.0,
                    label=f"{lbl} Orig",
                )
                ax_h.set_title(f"{lbl} Histogram", fontsize=7, color=PlotCanvas.DARK_FG)
                ax_h.set_xlim(0, 255)

                # Row 1: PDF
                ax_p = axes[1, i]
                ax_p.plot(range(256), analysis.pdf, color=color, linewidth=1.0, label=f"{lbl} Orig")
                ax_p.set_title(f"{lbl} PDF", fontsize=7, color=PlotCanvas.DARK_FG)
                ax_p.set_xlim(0, 255)

                # Overlay result if enabled and available
                if (
                    self._overlay_check.isChecked()
                    and self._result_analysis is not None
                    and i < len(self._result_analysis)
                ):
                    res_an = self._result_analysis[i]
                    res_col = self._OVERLAY_COLORS[lbl]
                    ax_h.bar(
                        range(256),
                        res_an.hist,
                        color=res_col,
                        alpha=0.4,
                        width=1.0,
                        label=f"{lbl} Res",
                    )
                    ax_p.plot(
                        range(256),
                        res_an.pdf,
                        color=res_col,
                        linewidth=1.0,
                        linestyle="--",
                        label=f"{lbl} Res",
                    )

            self._hist_plot.draw_now()
        except Exception:
            self._hist_plot.clear()

    def _render_cdf(self) -> None:
        """Plot per-channel Cumulative Distribution Function (CDF) curves."""
        if self._orig_data is None:
            self._cdf_plot.hide()
            self._cdf_placeholder.setText("Open an image to view CDF")
            self._cdf_placeholder.show()
            return

        analysis_list = (
            self._result_analysis if self._result_analysis is not None else self._orig_analysis
        )
        if analysis_list is None:
            self._cdf_plot.hide()
            self._cdf_placeholder.setText("CDF analysis not available yet (stub)")
            self._cdf_placeholder.show()
            return

        self._cdf_placeholder.hide()
        self._cdf_plot.show()

        is_gray = len(analysis_list) == 1
        labels = ["Gray"] if is_gray else ["R", "G", "B"]

        try:
            self._cdf_plot.clear()
            for analysis, lbl in zip(analysis_list, labels):
                color = self._CHANNEL_COLORS[lbl]
                self._cdf_plot.plot_curve(range(256), analysis.cdf, label=f"{lbl} CDF", color=color)
            self._cdf_plot.set_title("Cumulative Distribution Function (CDF)")
            self._cdf_plot.draw_now()
        except Exception:
            self._cdf_plot.clear()

    def _render_spectrum(self) -> None:
        """Display 2D Fourier Spectrum."""
        target_img = (
            self._result_array
            if self._result_array is not None
            else (self._orig_data.array if self._orig_data else None)
        )
        if target_img is None:
            self._spectrum_viewer.hide()
            self._spectrum_placeholder.setText("Open an image to view spectrum")
            self._spectrum_placeholder.show()
            return

        try:
            spec = self._freq_filter.spectrum(target_img)
            self._spectrum_placeholder.hide()
            self._spectrum_viewer.show()
            self._spectrum_viewer.set_image(spec)
        except NotImplementedError:
            self._spectrum_viewer.hide()
            self._spectrum_placeholder.setText("Fourier spectrum not available yet (stub)")
            self._spectrum_placeholder.show()
        except Exception:
            self._spectrum_viewer.hide()
            self._spectrum_placeholder.setText("Could not compute spectrum")
            self._spectrum_placeholder.show()

    def _render_details(self) -> None:
        """Display extra outputs (filter masks, hybrid components)."""
        if not self._extras:
            self._details_splitter.hide()
            self._details_placeholder.show()
            return

        self._details_placeholder.hide()
        self._details_splitter.show()

        keys = list(self._extras.keys())
        if len(keys) >= 1:
            k1 = keys[0]
            self._detail_viewer1.setTitle(f"Detail: {k1.upper()}")
            self._detail_viewer1.set_image(self._extras[k1])
            self._detail_viewer1.show()
        else:
            self._detail_viewer1.hide()

        if len(keys) >= 2:
            k2 = keys[1]
            self._detail_viewer2.setTitle(f"Detail: {k2.upper()}")
            self._detail_viewer2.set_image(self._extras[k2])
            self._detail_viewer2.show()
        else:
            self._detail_viewer2.hide()
