"""Shared widgets used by ALL tabs: ImageViewer, PlotCanvas, ParamPanel.

These are generic, reusable components that never hardcode any feature name.
The GUI builds all its controls dynamically from params_schema dictionaries.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# ---------------------------------------------------------------------------
# ImageViewer — titled panel showing a numpy image with zoom/pan
# ---------------------------------------------------------------------------


class ImageViewer(QGroupBox):
    """Titled panel that displays a numpy image (gray or RGB), scaled to fit.

    Features: mouse-wheel zoom, drag pan, double-click to reset.
    Shows image size and a 'Gray'/'RGB' badge in the title.
    """

    def __init__(self, title: str = "Image", parent=None):
        super().__init__(title, parent)
        self._title_base = title
        self._current: np.ndarray | None = None

        # Scroll area for zoom/pan
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Label that holds the pixmap
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._scroll.setWidget(self._label)

        layout = QVBoxLayout()
        layout.addWidget(self._scroll)
        self.setLayout(layout)

        self._pixmap: QPixmap | None = None
        self._zoom = 1.0

        # Drag-pan state
        self._dragging = False
        self._drag_start = None
        self._scroll_start_h = 0
        self._scroll_start_v = 0

        self._label.installEventFilter(self)
        self._scroll.viewport().installEventFilter(self)

    # -- Public API --

    @property
    def current(self) -> np.ndarray | None:
        """Last displayed image array (or None)."""
        return self._current

    def set_image(self, array: np.ndarray | None) -> None:
        """Show a numpy image (HxW gray or HxWx3 RGB). None or empty clears."""
        if array is None or not isinstance(array, np.ndarray) or array.size == 0:
            self.clear()
            return
        self._current = array
        self._pixmap = self._array_to_pixmap(array)
        self._zoom = 1.0
        self._update_display()
        self._update_title()

    def clear(self) -> None:
        """Clear the viewer."""
        self._current = None
        self._pixmap = None
        self._label.clear()
        self.setTitle(self._title_base)

    def set_title_base(self, title: str) -> None:
        """Update the base title and refresh badge display."""
        self._title_base = title
        self._update_title()

    # -- Internal helpers --

    def _update_title(self) -> None:
        """Update the group-box title with size + Gray/RGB badge."""
        if self._current is None:
            self.setTitle(self._title_base)
            return
        h, w = self._current.shape[:2]
        mode = "Gray" if self._current.ndim == 2 else "RGB"
        self.setTitle(f"{self._title_base}  [{w}×{h}]  {mode}")

    def _update_display(self) -> None:
        """Redraw the pixmap at the current zoom level."""
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self._pixmap.size() * self._zoom,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())

    @staticmethod
    def _array_to_pixmap(array: np.ndarray) -> QPixmap:
        """Convert a numpy array (HxW or HxWx3 uint8) to a QPixmap."""
        array = np.ascontiguousarray(array)
        if array.ndim == 2:
            h, w = array.shape
            qimage = QImage(array.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            h, w, _ = array.shape
            qimage = QImage(array.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimage.copy())

    # -- Event handling for zoom / pan --

    def eventFilter(self, obj, event):
        """Handle wheel-zoom, drag-pan, and double-click-reset."""
        if event.type() == event.Type.Wheel and self._pixmap is not None:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            self._zoom = max(0.1, min(10.0, self._zoom * factor))
            self._update_display()
            return True

        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._dragging = True
                self._drag_start = event.globalPosition().toPoint()
                self._scroll_start_h = self._scroll.horizontalScrollBar().value()
                self._scroll_start_v = self._scroll.verticalScrollBar().value()
                return True

        if event.type() == event.Type.MouseMove and self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_start
            self._scroll.horizontalScrollBar().setValue(self._scroll_start_h - delta.x())
            self._scroll.verticalScrollBar().setValue(self._scroll_start_v - delta.y())
            return True

        if event.type() == event.Type.MouseButtonRelease:
            self._dragging = False
            return True

        if event.type() == event.Type.MouseButtonDblClick:
            self._zoom = 1.0
            self._update_display()
            return True

        return super().eventFilter(obj, event)


# ---------------------------------------------------------------------------
# PlotCanvas — matplotlib figure for histograms / curves (dark style)
# ---------------------------------------------------------------------------


class PlotCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas with a dark theme, used for histograms and curves.

    API: clear(), set_title(), plot_histogram(), plot_curve(), draw_now(),
    subplots(rows, cols) returning axes for side-by-side plots.
    """

    DARK_BG = "#1e1e2e"
    DARK_FG = "#cdd6f4"

    def __init__(self, parent=None, width=5, height=3, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor(self.DARK_BG)
        self.axes = self.fig.add_subplot(111)
        self._style_axes(self.axes)
        super().__init__(self.fig)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _style_axes(self, ax) -> None:
        """Apply dark styling to an axes object."""
        ax.set_facecolor(self.DARK_BG)
        ax.tick_params(colors=self.DARK_FG, labelsize=7)
        ax.xaxis.label.set_color(self.DARK_FG)
        ax.yaxis.label.set_color(self.DARK_FG)
        ax.title.set_color(self.DARK_FG)
        for spine in ax.spines.values():
            spine.set_color(self.DARK_FG)

    def clear(self) -> None:
        """Clear all axes."""
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        self._style_axes(self.axes)
        self.draw_idle()

    def set_title(self, text: str) -> None:
        """Set title for the main axes."""
        self.axes.set_title(text, fontsize=9, color=self.DARK_FG)

    def plot_histogram(self, hist: np.ndarray, color: str = "white", label: str | None = None):
        """Plot a 256-bin histogram as a bar chart."""
        self.axes.bar(range(len(hist)), hist, color=color, alpha=0.6, width=1.0, label=label)
        if label:
            self.axes.legend(fontsize=7, facecolor=self.DARK_BG, edgecolor=self.DARK_FG)

    def plot_curve(self, x, y, label: str | None = None, color: str | None = None):
        """Plot a curve (PDF, CDF, etc.)."""
        kwargs = {}
        if label:
            kwargs["label"] = label
        if color:
            kwargs["color"] = color
        self.axes.plot(x, y, linewidth=1.2, **kwargs)
        if label:
            self.axes.legend(fontsize=7, facecolor=self.DARK_BG, edgecolor=self.DARK_FG)

    def subplots(self, rows: int, cols: int):
        """Clear and create a grid of subplots, returning a list/array of axes."""
        self.fig.clear()
        axes = self.fig.subplots(rows, cols)
        # Style every axes
        if isinstance(axes, np.ndarray):
            for ax in axes.flat:
                self._style_axes(ax)
        else:
            self._style_axes(axes)
        self.fig.tight_layout(pad=1.5)
        return axes

    def draw_now(self) -> None:
        """Force an immediate redraw."""
        self.fig.tight_layout(pad=1.5)
        self.draw()


# ---------------------------------------------------------------------------
# ParamPanel — dynamic control panel built from a params_schema dict
# ---------------------------------------------------------------------------


class ParamPanel(QGroupBox):
    """Builds controls from a params_schema dictionary. Never hardcodes feature names.

    int/float  -> slider + spin box (kept in sync, respecting min/max/step).
    select     -> combo box.
    For kernel_size, keeps values odd (step forced to 2 if step is odd-aware).
    Emits 'changed' signal (debounced 250ms) when any value changes.
    """

    changed = Signal()

    def __init__(self, params_schema: dict = None, parent=None):
        super().__init__("Parameters", parent)
        self._schema: dict = {}
        self._controls: dict = {}  # key -> widget (QSpinBox | QDoubleSpinBox | QComboBox)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        # Debounce timer: emit 'changed' only after 250 ms of inactivity
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self.changed.emit)

        if params_schema:
            self.set_schema(params_schema)

    def set_schema(self, schema: dict) -> None:
        """Rebuild all controls from a new schema (called when the dropdown changes)."""
        # Clear existing widgets
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        self._schema = schema
        self._controls = {}

        for key, spec in schema.items():
            ptype = spec.get("type", "int")

            if ptype == "select":
                self._add_combo(key, spec)
            elif ptype == "float":
                self._add_slider_spin(key, spec, is_float=True)
            else:
                self._add_slider_spin(key, spec, is_float=False)

    def values(self) -> dict:
        """Return current parameter values as a dict."""
        result = {}
        for key, widget in self._controls.items():
            if isinstance(widget, QComboBox):
                result[key] = widget.currentText()
            else:
                result[key] = widget.value()
        return result

    # -- Private helpers --

    def _add_combo(self, key: str, spec: dict) -> None:
        """Add a combo box for a 'select' type parameter."""
        label = spec.get("label", key)
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        combo = QComboBox()
        combo.addItems([str(o) for o in spec.get("options", [])])
        default = spec.get("default")
        if default is not None:
            idx = combo.findText(str(default))
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.currentTextChanged.connect(self._on_value_changed)
        row.addWidget(combo)
        self._controls[key] = combo
        container = QWidget()
        container.setLayout(row)
        self._layout.addWidget(container)

    def _add_slider_spin(self, key: str, spec: dict, is_float: bool) -> None:
        """Add a slider + spin box pair for int or float parameters."""
        label = spec.get("label", key)
        lo = spec.get("min", 0)
        hi = spec.get("max", 100)
        step = spec.get("step", 1)
        default = spec.get("default", lo)

        # For kernel_size ensure odd values only
        is_kernel = "kernel" in key.lower()
        if is_kernel:
            step = 2

        row = QHBoxLayout()
        row.addWidget(QLabel(label))

        if is_float:
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(step)
            spin.setDecimals(max(2, len(str(step).split(".")[-1]) if "." in str(step) else 0))
            spin.setValue(default)
        else:
            spin = QSpinBox()
            spin.setRange(int(lo), int(hi))
            spin.setSingleStep(int(step))
            spin.setValue(int(default))

        # Slider (integer representation)
        slider = QSlider(Qt.Orientation.Horizontal)
        if is_float:
            # Map float range to integer slider with scaling
            scale = max(1, int(1.0 / step)) if step < 1 else 1
            slider.setRange(int(lo * scale), int(hi * scale))
            slider.setSingleStep(int(step * scale))
            slider.setValue(int(default * scale))

            def _on_slider(val, s=spin, sc=scale):
                s.blockSignals(True)
                s.setValue(val / sc)
                s.blockSignals(False)
                self._on_value_changed()

            def _on_spin(val, sl=slider, sc=scale):
                sl.blockSignals(True)
                sl.setValue(int(val * sc))
                sl.blockSignals(False)
                self._on_value_changed()

            slider.valueChanged.connect(_on_slider)
            spin.valueChanged.connect(_on_spin)
        else:
            slider.setRange(int(lo), int(hi))
            slider.setSingleStep(int(step))
            slider.setValue(int(default))

            def _on_slider_int(val, s=spin, is_k=is_kernel):
                if is_k:
                    val = val | 1  # force odd
                s.blockSignals(True)
                s.setValue(val)
                s.blockSignals(False)
                self._on_value_changed()

            def _on_spin_int(val, sl=slider, is_k=is_kernel):
                if is_k:
                    val = val | 1  # force odd
                sl.blockSignals(True)
                sl.setValue(val)
                sl.blockSignals(False)
                self._on_value_changed()

            slider.valueChanged.connect(_on_slider_int)
            spin.valueChanged.connect(_on_spin_int)

        row.addWidget(slider)
        row.addWidget(spin)

        self._controls[key] = spin
        container = QWidget()
        container.setLayout(row)
        self._layout.addWidget(container)

    def _on_value_changed(self, *_) -> None:
        """Restart the debounce timer on every value change."""
        self._debounce.start()
