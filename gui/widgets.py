"""Shared widgets used by ALL tabs: ImageViewer, PlotCanvas, ParamPanel.

These are generic, reusable components that never hardcode any feature name.
The GUI builds all its controls dynamically from params_schema dictionaries.
"""

from PySide6.QtCore import Qt, Signal, QTimer, QSize
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
    QPushButton,
)

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# ---------------------------------------------------------------------------
# ImageViewer - titled panel showing a numpy image with zoom/pan
# ---------------------------------------------------------------------------


class ImageViewer(QGroupBox):
    """Titled panel that displays a numpy image (gray or RGB), scaled to fit.

    The image auto-fits the available panel area while keeping aspect ratio.
    Features: mouse-wheel zoom, drag pan, double-click / Fit button to reset.
    Shows image size and a Gray/RGB badge in the title.
    Re-fits automatically on window/panel resize.
    """

    def __init__(self, title: str = "Image", parent=None):
        super().__init__(title, parent)
        self._title_base = title
        self._current = None  # np.ndarray | None

        # Scroll area for zoom/pan
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Label that holds the pixmap
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setWidget(self._label)

        # Fit button
        self._fit_btn = QPushButton("Fit")
        self._fit_btn.setFixedSize(44, 22)
        self._fit_btn.setToolTip("Fit image to panel (double-click also works)")
        self._fit_btn.setStyleSheet(
            "QPushButton { font-size: 10px; padding: 2px 4px; border-radius: 4px; }"
        )
        self._fit_btn.clicked.connect(self._reset_zoom)

        # Header row with Fit button flush right
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch()
        header_layout.addWidget(self._fit_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.addWidget(header)
        layout.addWidget(self._scroll, 1)
        self.setLayout(layout)

        self._pixmap = None  # QPixmap | None
        self._zoom = 1.0  # 1.0 == fit-to-panel mode

        # Drag-pan state
        self._dragging = False
        self._drag_start = None
        self._scroll_start_h = 0
        self._scroll_start_v = 0

        # Debounced resize handler
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(60)
        self._resize_timer.timeout.connect(self._on_resize_debounced)

        self._label.installEventFilter(self)
        self._scroll.viewport().installEventFilter(self)

    # -- Public API --

    @property
    def current(self):
        """Last displayed image array (or None)."""
        return self._current

    def set_image(self, array) -> None:
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
        self._label.resize(QSize(0, 0))
        self.setTitle(self._title_base)

    def set_title_base(self, title: str) -> None:
        """Update the base title and refresh badge display."""
        self._title_base = title
        self._update_title()

    # -- Internal helpers --

    def _viewport_size(self) -> QSize:
        """Available content area of the scroll area."""
        return self._scroll.viewport().size()

    def _reset_zoom(self) -> None:
        """Reset to fit-to-panel mode."""
        self._zoom = 1.0
        self._update_display()

    def _update_title(self) -> None:
        """Update the group-box title with size + Gray/RGB badge."""
        if self._current is None:
            self.setTitle(self._title_base)
            return
        h, w = self._current.shape[:2]
        mode = "Gray" if self._current.ndim == 2 else "RGB"
        self.setTitle(f"{self._title_base}  [{w}x{h}]  {mode}")

    def _update_display(self) -> None:
        """Redraw the pixmap scaled to fit the viewport at the current zoom level."""
        if self._pixmap is None:
            return
        vp = self._viewport_size()
        if vp.width() < 4 or vp.height() < 4:
            return
        if self._zoom == 1.0:
            # Fit mode: scale to fill viewport keeping aspect ratio
            scaled = self._pixmap.scaled(
                vp,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            # Manual zoom: scale relative to native pixmap size
            native = self._pixmap.size()
            target = QSize(
                max(1, int(native.width() * self._zoom)),
                max(1, int(native.height() * self._zoom)),
            )
            scaled = self._pixmap.scaled(
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())

    def _on_resize_debounced(self) -> None:
        """Called after resize events settle; re-fits the image if in fit mode."""
        if self._zoom == 1.0:
            self._update_display()

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

    # -- Event handling for zoom / pan / resize --

    def resizeEvent(self, event) -> None:
        """Trigger a debounced re-fit when the panel is resized."""
        super().resizeEvent(event)
        self._resize_timer.start()

    def eventFilter(self, obj, event):
        """Handle viewport resize, wheel-zoom, drag-pan, and double-click-reset."""
        # Viewport resize - re-fit if in fit mode
        if obj is self._scroll.viewport() and event.type() == event.Type.Resize:
            self._resize_timer.start()
            return False

        if event.type() == event.Type.Wheel and self._pixmap is not None:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            # Transition from fit-mode: compute equivalent zoom factor first
            if self._zoom == 1.0:
                vp = self._viewport_size()
                native = self._pixmap.size()
                fit_w = vp.width() / native.width()
                fit_h = vp.height() / native.height()
                self._zoom = min(fit_w, fit_h)
            self._zoom = max(0.05, min(20.0, self._zoom * factor))
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
            self._reset_zoom()
            return True

        return super().eventFilter(obj, event)


# ---------------------------------------------------------------------------
# PlotCanvas - matplotlib figure for histograms / curves (dark style)
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

    def plot_histogram(self, hist: np.ndarray, color: str = "white", label=None):
        """Plot a 256-bin histogram as a bar chart."""
        self.axes.bar(range(len(hist)), hist, color=color, alpha=0.6, width=1.0, label=label)
        if label:
            self.axes.legend(fontsize=7, facecolor=self.DARK_BG, edgecolor=self.DARK_FG)

    def plot_curve(self, x, y, label=None, color=None):
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
# ParamPanel - dynamic control panel built from a params_schema dict
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
        self._controls: dict = {}  # key -> widget
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self.changed.emit)

        if params_schema:
            self.set_schema(params_schema)

    def set_feature(self, feature_name: str, schema: dict) -> None:
        """Update title with the active feature name and rebuild parameter controls."""
        self.setTitle(f"Parameters: {feature_name}")
        self.set_schema(schema)

    def set_schema(self, schema: dict) -> None:
        """Rebuild all controls from a new schema."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        self._schema = schema
        self._controls = {}

        if not schema:
            empty_lbl = QLabel("No adjustable parameters for this operation.")
            empty_lbl.setStyleSheet("color: #6c7086; font-style: italic; padding: 6px;")
            self._layout.addWidget(empty_lbl)
            return

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

        slider = QSlider(Qt.Orientation.Horizontal)
        if is_float:
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
                    val = val | 1
                s.blockSignals(True)
                s.setValue(val)
                s.blockSignals(False)
                self._on_value_changed()

            def _on_spin_int(val, sl=slider, is_k=is_kernel):
                if is_k:
                    val = val | 1
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
