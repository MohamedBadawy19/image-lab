"""ImageLab Studio Main Window — Single-Window 3-Pane Layout.

Layout:
- Left Sidebar: Upload, Feature Picker, Parameters, and Actions.
- Right Splitter (3 equal panes by default):
  1. Original: ImageViewer showing the current working image.
  2. Result: Interactive ImageViewer with single / 3-grid views and hybrid scaling.
  3. Analysis: AnalysisPanel with Histogram, CDF, Spectrum, and Details tabs.

Features drag & drop image loading, chained workflow (Ctrl+U), non-destructive
pipeline, and safe execution with centralized error handling.
"""

import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.base import UnsupportedImageError
from core.image_data import ImageData
from gui.analysis_panel import AnalysisPanel
from gui.error_handler import run_safely, show_error
from gui.features import FeatureEntry, FeatureOutput, run_feature
from gui.sidebar import Sidebar
from gui.widgets import ImageViewer

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Single-window Image Studio application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageLab — Studio")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 880)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Application State
        self._image_data: ImageData | None = None
        self._second_image_data: ImageData | None = None
        self._original_path: str | None = None
        self._read_as_gray: bool = False
        self._history: list[str] = []
        self._last_result: np.ndarray | None = None
        self._last_extras: dict[str, np.ndarray] = {}
        self._edge_view_mode: str = "combined"  # "combined" | "gx" | "gy" | "all"

        # Build UI
        self._setup_menus()
        self._setup_ui()
        self._setup_status_bar()
        self._connect_signals()

    # ------------------------------------------------------------------ UI Setup

    def _setup_menus(self) -> None:
        """Create File and Edit menus with keyboard shortcuts."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        open_act = QAction("&Open image", self)
        open_act.setShortcut(QKeySequence("Ctrl+O"))
        open_act.triggered.connect(self._on_open_image_dialog)
        file_menu.addAction(open_act)

        save_act = QAction("&Save result", self)
        save_act.setShortcut(QKeySequence("Ctrl+S"))
        save_act.triggered.connect(self._on_save_result)
        file_menu.addAction(save_act)

        file_menu.addSeparator()
        exit_act = QAction("E&xit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")

        commit_act = QAction("&Use result as new input", self)
        commit_act.setShortcut(QKeySequence("Ctrl+U"))
        commit_act.triggered.connect(self._on_commit_result)
        edit_menu.addAction(commit_act)

        reset_act = QAction("&Reset to original", self)
        reset_act.setShortcut(QKeySequence("Ctrl+R"))
        reset_act.triggered.connect(self._on_reset_original)
        edit_menu.addAction(reset_act)

    def _setup_ui(self) -> None:
        """Assemble the sidebar and 3-pane right workspace."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Left Sidebar
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # 2. Right Splitter (Original | Result | Analysis)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Pane 1: Original
        self._viewer_orig = ImageViewer("Original")
        self._splitter.addWidget(self._viewer_orig)

        # Pane 2: Result Container
        result_container = self._create_result_container()
        self._splitter.addWidget(result_container)

        # Pane 3: Analysis Panel
        self._analysis_panel = AnalysisPanel()
        self._splitter.addWidget(self._analysis_panel)

        # Equal widths by default
        self._splitter.setSizes([380, 380, 380])
        main_layout.addWidget(self._splitter, 1)

    def _create_result_container(self) -> QWidget:
        """Build the Result pane with stacked single viewer / 3-grid edge view."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Stacked widget for normal vs 3-grid view
        self._result_stack = QStackedWidget()

        # Page 0: Single Result Viewer
        self._viewer_result = ImageViewer("Result")
        self._result_stack.addWidget(self._viewer_result)

        # Page 1: 3-Grid View (X, Y, Combined)
        grid_widget = QWidget()
        grid_layout = QVBoxLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_splitter = QSplitter(Qt.Orientation.Vertical)
        self._viewer_gx = ImageViewer("Gradient X")
        self._viewer_gy = ImageViewer("Gradient Y")
        self._viewer_mag = ImageViewer("Combined Magnitude")
        self._grid_splitter.addWidget(self._viewer_gx)
        self._grid_splitter.addWidget(self._viewer_gy)
        self._grid_splitter.addWidget(self._viewer_mag)
        grid_layout.addWidget(self._grid_splitter)
        self._result_stack.addWidget(grid_widget)

        layout.addWidget(self._result_stack, 1)

        # Hybrid Preview Scale bar (visible only for Hybrid)
        self._scale_bar = QWidget()
        scale_layout = QHBoxLayout(self._scale_bar)
        scale_layout.setContentsMargins(4, 2, 4, 2)
        scale_layout.addWidget(QLabel("🔍 Hybrid Preview Scale %:"))

        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(10, 100)
        self._scale_slider.setValue(100)

        self._scale_spin = QSpinBox()
        self._scale_spin.setRange(10, 100)
        self._scale_spin.setValue(100)

        self._scale_slider.valueChanged.connect(self._scale_spin.setValue)
        self._scale_spin.valueChanged.connect(self._scale_slider.setValue)
        self._scale_slider.valueChanged.connect(self._on_scale_changed)

        scale_layout.addWidget(self._scale_slider)
        scale_layout.addWidget(self._scale_spin)
        self._scale_bar.setVisible(False)
        layout.addWidget(self._scale_bar)

        return container

    def _setup_status_bar(self) -> None:
        """Create and configure the status bar."""
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._update_status()

    def _connect_signals(self) -> None:
        """Connect all sidebar signals to MainWindow handler methods."""
        self._sidebar.open_requested.connect(self._on_open_image_dialog)
        self._sidebar.second_image_requested.connect(self._on_open_second_image_dialog)
        self._sidebar.read_mode_toggled.connect(self._on_toggle_read_mode)
        self._sidebar.feature_selected.connect(self._on_feature_selected)
        self._sidebar.apply_requested.connect(self._on_apply_feature)
        self._sidebar.commit_requested.connect(self._on_commit_result)
        self._sidebar.reset_requested.connect(self._on_reset_original)
        self._sidebar.save_requested.connect(self._on_save_result)
        self._sidebar.edge_view_changed.connect(self._on_edge_view_changed)

    # ------------------------------------------------------------------ Image Loading & Drag-and-Drop

    def _load_image_file(self, path: str, as_gray: bool = False) -> None:
        """Load an image file and initialize workspace."""
        data = run_safely(ImageData.load, path, as_gray, parent=self)
        if data is None:
            return

        self._original_path = path
        self._read_as_gray = as_gray
        self._image_data = data
        self._history = ["Original"]
        self._last_result = None
        self._last_extras = {}

        self._viewer_orig.set_image(data.array)
        self._viewer_result.clear()
        self._viewer_gx.clear()
        self._viewer_gy.clear()
        self._viewer_mag.clear()

        self._analysis_panel.set_original(data)
        self._sidebar.set_controls_enabled(True)
        self._sidebar.set_history(self._history)
        self._sidebar.set_read_mode(as_gray)
        self._update_status()

    def _on_open_image_dialog(self) -> None:
        """Prompt file dialog to open an image."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All files (*)",
        )
        if path:
            self._load_image_file(path, self._read_as_gray)

    def _on_open_second_image_dialog(self) -> None:
        """Prompt file dialog to load the second image for hybrid processing."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Second Image (Hybrid)",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All files (*)",
        )
        if path:
            data = run_safely(ImageData.load, path, self._read_as_gray, parent=self)
            if data is not None:
                self._second_image_data = data
                self._sidebar.set_second_image(data)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept file drag events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle image file drops."""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self._load_image_file(path, self._read_as_gray)

    # ------------------------------------------------------------------ Actions & Pipeline

    def _on_feature_selected(self, entry: FeatureEntry) -> None:
        """Handle feature selection change in sidebar."""
        is_hybrid = entry.group == "Hybrid"
        self._scale_bar.setVisible(is_hybrid)

    def _on_apply_feature(self) -> None:
        """Execute currently selected feature with current parameters."""
        if self._image_data is None:
            show_error(UnsupportedImageError("Open an image first."), parent=self)
            return

        entry = self._sidebar.selected_feature
        if entry is None:
            return

        params = self._sidebar.current_params

        output: FeatureOutput | None = run_safely(
            run_feature,
            entry,
            self._image_data,
            params,
            self._second_image_data,
            parent=self,
        )

        if output is None:
            return

        self._last_result = output.result
        self._last_extras = output.extras

        # Update Result View
        self._update_result_display()

        # Update Analysis Panel
        self._analysis_panel.set_result(output.result, output.extras)

    def _update_result_display(self) -> None:
        """Render the result in either single view or 3-grid edge view."""
        if self._last_result is None:
            return

        entry = self._sidebar.selected_feature
        is_edge = entry is not None and entry.group == "Edges" and entry.has_xy

        if is_edge and self._edge_view_mode == "all":
            # Switch to 3-Grid View
            self._result_stack.setCurrentIndex(1)
            self._viewer_mag.set_image(self._last_result)
            if "gx" in self._last_extras:
                self._viewer_gx.set_image(self._last_extras["gx"])
            if "gy" in self._last_extras:
                self._viewer_gy.set_image(self._last_extras["gy"])
        else:
            # Single Viewer View
            self._result_stack.setCurrentIndex(0)
            if is_edge and self._edge_view_mode == "gx" and "gx" in self._last_extras:
                self._viewer_result.set_title_base("Gradient X")
                self._viewer_result.set_image(self._last_extras["gx"])
            elif is_edge and self._edge_view_mode == "gy" and "gy" in self._last_extras:
                self._viewer_result.set_title_base("Gradient Y")
                self._viewer_result.set_image(self._last_extras["gy"])
            else:
                self._viewer_result.set_title_base("Result")
                self._apply_result_with_scale(self._last_result)

    def _apply_result_with_scale(self, image: np.ndarray) -> None:
        """Display result respecting the hybrid preview scale if applicable."""
        entry = self._sidebar.selected_feature
        if entry is not None and entry.group == "Hybrid":
            scale = self._scale_slider.value() / 100.0
            if scale < 1.0:
                import cv2

                h, w = image.shape[:2]
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                self._viewer_result.set_image(scaled)
                return

        self._viewer_result.set_image(image)

    def _on_scale_changed(self, _) -> None:
        """Handle hybrid preview scale slider change."""
        if self._last_result is not None:
            self._apply_result_with_scale(self._last_result)

    def _on_edge_view_changed(self, mode: str) -> None:
        """Handle edge view mode change (combined / gx / gy / all)."""
        self._edge_view_mode = mode
        self._update_result_display()

    def _on_commit_result(self) -> None:
        """Use result as new input (Ctrl+U) to chain operations."""
        if self._last_result is None:
            show_error(Exception("No result to use. Apply an operation first."), parent=self)
            return

        # Wrap in ImageData
        new_data = ImageData.from_array(self._last_result, self._original_path)
        self._image_data = new_data

        # Update History
        entry = self._sidebar.selected_feature
        name = entry.name if entry else "Operation"
        self._history.append(name)

        # Refresh UI
        self._viewer_orig.set_image(new_data.array)
        self._viewer_result.clear()
        self._last_result = None
        self._last_extras = {}

        self._sidebar.set_history(self._history)
        self._analysis_panel.set_original(new_data)
        self._update_status()

    def _on_reset_original(self) -> None:
        """Reload original file and reset pipeline."""
        if self._original_path is None:
            show_error(Exception("No original image to reset to."), parent=self)
            return

        self._load_image_file(self._original_path, self._read_as_gray)

    def _on_save_result(self) -> None:
        """Save the last result to disk (Ctrl+S)."""
        if self._last_result is None:
            show_error(Exception("No result to save. Apply an operation first."), parent=self)
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Result",
            "",
            "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp);;TIFF (*.tif)",
        )
        if path:
            run_safely(ImageData.save, path, self._last_result, parent=self)

    def _on_toggle_read_mode(self, as_gray: bool) -> None:
        """Handle RGB vs Gray reading mode toggle."""
        if self._original_path and len(self._history) > 1:
            reply = QMessageBox.question(
                self,
                "Restart from original?",
                "This restarts from the original file. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self._sidebar.set_read_mode(self._read_as_gray)
                return

        self._read_as_gray = as_gray
        if self._original_path:
            self._load_image_file(self._original_path, as_gray)

    # ------------------------------------------------------------------ Status Bar

    def _update_status(self) -> None:
        """Update status bar information."""
        parts = []
        if self._image_data:
            if self._original_path:
                parts.append(Path(self._original_path).name)
            h, w = self._image_data.shape[:2]
            parts.append(f"{w}×{h}")
            parts.append("Gray" if self._image_data.is_gray else "RGB")
        if self._history:
            parts.append(" > ".join(self._history))
        self._status.showMessage(
            "   |   ".join(parts)
            if parts
            else "No image loaded — Open an image or drag & drop to begin"
        )
