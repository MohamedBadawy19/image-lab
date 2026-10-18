"""ImageLab Studio Main Window - Rebuilt Main Layout.

Layout:
- LEFT: Features sidebar (same features, behavior, names, own scrollbar).
- RIGHT, TOP: Row of image windows (Original + Result in normal modes; Image A + Image B + Result in Hybrid mode). Never scrolls.
- RIGHT, BOTTOM: Tables and diagrams area (Histogram, CDF, Spectrum, Details tabs).
- A scroller at the bottom that controls the graphs area ONLY; appears only when graphs overflow.
- Vertical splitter between images area (~55%) and graphs area (~45%).
- Auto-fit with aspect-ratio preservation, zoom/pan linking, untouched Original image lifecycle.
"""

import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
from gui.widgets import ImageViewer, JumpSlider

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Single-window Image Studio application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageLab - Studio")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 880)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Application State
        self._image_data: ImageData | None = None       # current working image
        self._first_image_data: ImageData | None = None # very first loaded image for true Reset
        self._second_image_data: ImageData | None = None
        self._original_path: str | None = None
        self._second_image_path: str | None = None
        self._read_as_gray: bool = False
        self._history: list[str] = []
        self._last_result: np.ndarray | None = None
        self._last_extras: dict[str, np.ndarray] = {}
        self._edge_view_mode: str = "combined"  # "combined" | "gx" | "gy" | "all"
        self._edge_window: QDialog | None = None
        self._edge_win_gx: ImageViewer | None = None
        self._edge_win_gy: ImageViewer | None = None
        self._edge_win_mag: ImageViewer | None = None

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
        """Assemble the sidebar and the 2-tier right workspace (Images top, Graphs bottom)."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Left Sidebar
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # 2. Right Vertical Splitter (Top: Images Row, Bottom: Graphs Area with scroller)
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Pane 1 (Top): Images Area (never scrolls)
        self._images_area = self._create_images_area()
        self._v_splitter.addWidget(self._images_area)

        # Pane 2 (Bottom): Graphs Area wrapped in a dedicated QScrollArea
        self._graphs_scroll = QScrollArea()
        self._graphs_scroll.setWidgetResizable(True)
        self._graphs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._graphs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._graphs_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._analysis_panel = AnalysisPanel()
        self._graphs_scroll.setWidget(self._analysis_panel)
        self._v_splitter.addWidget(self._graphs_scroll)

        # Proportions: about 55% images, 45% graphs
        self._v_splitter.setSizes([480, 390])
        main_layout.addWidget(self._v_splitter, 1)

    def _create_images_area(self) -> QWidget:
        """Build the top images row container.

        Contains:
        - Top bar with comparison controls (Link Zoom & Pan, Fit All).
        - Horizontal splitter with the image windows:
          - Normal mode: Original and Result (equal size).
          - Hybrid mode: Image A, Image B, Result (equal size).
        - Hybrid preview scale bar (visible only in Hybrid mode).
        The images area NEVER scrolls.
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Top comparison bar
        bar = QWidget()
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(4, 2, 4, 2)
        bar_layout.setSpacing(8)

        ws_label = QLabel("Image Workspace")
        ws_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #89b4fa;")
        bar_layout.addWidget(ws_label)

        # Order completion badge indicator
        self._completion_badge = QLabel("")
        self._completion_badge.setStyleSheet("""
            QLabel {
                background-color: #a6e3a1;
                color: #11111b;
                font-weight: bold;
                font-size: 11px;
                padding: 2px 10px;
                border-radius: 4px;
            }
        """)
        self._completion_badge.setVisible(False)
        bar_layout.addWidget(self._completion_badge)

        bar_layout.addStretch()

        self._link_zoom_check = QCheckBox("Link Zoom & Pan")
        self._link_zoom_check.setChecked(True)
        self._link_zoom_check.setToolTip("Synchronize zoom level and panning between image windows")
        self._link_zoom_check.setStyleSheet("color: #cdd6f4; font-size: 11px;")
        bar_layout.addWidget(self._link_zoom_check)

        self._btn_fit_all = QPushButton("Fit All")
        self._btn_fit_all.setFixedHeight(22)
        self._btn_fit_all.setStyleSheet("font-size: 10px; padding: 2px 8px; border-radius: 4px;")
        self._btn_fit_all.setToolTip("Fit all visible images to their windows")
        self._btn_fit_all.clicked.connect(self._on_fit_all)
        bar_layout.addWidget(self._btn_fit_all)

        layout.addWidget(bar)

        # Horizontal Splitter for image windows
        self._images_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Viewer 1: Original (or Image A in Hybrid)
        self._viewer_orig = ImageViewer("Original")
        self._images_splitter.addWidget(self._viewer_orig)

        # Viewer 2: Image B (hidden in normal mode, shown in Hybrid mode)
        self._viewer_img_b = ImageViewer("Image B")
        self._viewer_img_b.setVisible(False)
        self._images_splitter.addWidget(self._viewer_img_b)

        # Viewer 3: Result container (holds single viewer or 3-grid)
        self._result_container = self._create_result_container()
        self._images_splitter.addWidget(self._result_container)

        self._update_images_splitter_sizes()
        layout.addWidget(self._images_splitter, 1)

        # Hybrid Preview Scale bar (visible only for Hybrid)
        self._scale_bar = QWidget()
        scale_layout = QHBoxLayout(self._scale_bar)
        scale_layout.setContentsMargins(4, 2, 4, 2)
        scale_layout.addWidget(QLabel("Hybrid Preview Scale %:"))

        self._scale_slider = JumpSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(10, 100)
        self._scale_slider.setValue(100)

        self._scale_spin = QSpinBox()
        self._scale_spin.setRange(10, 100)
        self._scale_spin.setValue(100)
        self._scale_spin.setStyleSheet("""
            QSpinBox {
                background: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 2px 4px;
                color: #cdd6f4;
                font-size: 11px;
                min-width: 58px;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid #45475a;
                border-bottom: 1px solid #45475a;
                background: #313244;
            }
            QSpinBox::up-button:hover {
                background: #45475a;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 16px;
                border-left: 1px solid #45475a;
                background: #313244;
            }
            QSpinBox::down-button:hover {
                background: #45475a;
            }
        """)

        self._scale_slider.valueChanged.connect(self._scale_spin.setValue)
        self._scale_spin.valueChanged.connect(self._scale_slider.setValue)
        self._scale_slider.valueChanged.connect(self._on_scale_changed)

        scale_layout.addWidget(self._scale_slider)
        scale_layout.addWidget(self._scale_spin)
        self._scale_bar.setVisible(False)
        layout.addWidget(self._scale_bar)

        # Connect linked zoom/pan signals
        for v in (self._viewer_orig, self._viewer_img_b, self._viewer_result):
            v.zoom_pan_changed.connect(self._on_viewer_zoom_pan_changed)

        return container

    def _create_result_container(self) -> QWidget:
        """Build the Result container with stacked single viewer / 3-grid edge view."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

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
        self._sidebar.params_changed.connect(self._on_params_changed)

    # ------------------------------------------------------------------ Image Loading & Drag-and-Drop

    def _load_image_file(self, path: str, as_gray: bool = False) -> None:
        """Load an image file and initialize workspace."""
        data = run_safely(ImageData.load, path, as_gray, parent=self)
        if data is None:
            return

        self._original_path = path
        self._read_as_gray = as_gray
        self._image_data = data
        # Remember the very first loaded image so Reset always goes back to it
        self._first_image_data = data
        self._history = ["Original"]
        self._last_result = None
        self._last_extras = {}

        # Original panel shows the loaded image; Result is cleared
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
                self._second_image_path = path
                self._second_image_data = data
                self._sidebar.set_second_image(data)
                self._viewer_img_b.set_image(data.array)
                if self._sidebar.is_live_preview:
                    self._on_apply_feature()

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

        # Switch image row: 3 viewers in Hybrid, 2 viewers in normal
        self._viewer_img_b.setVisible(is_hybrid)
        self._update_images_splitter_sizes()

        # In hybrid mode, restore Image B if available
        if is_hybrid:
            if self._second_image_data is not None:
                self._viewer_img_b.set_image(self._second_image_data.array)
            if self._link_zoom_check.isChecked() and self._viewer_orig._zoom != 1.0:
                h_max = max(1, self._viewer_orig._scroll.horizontalScrollBar().maximum())
                v_max = max(1, self._viewer_orig._scroll.verticalScrollBar().maximum())
                h_ratio = self._viewer_orig._scroll.horizontalScrollBar().value() / h_max
                v_ratio = self._viewer_orig._scroll.verticalScrollBar().value() / v_max
                self._viewer_img_b.sync_view(self._viewer_orig._zoom, h_ratio, v_ratio)
        else:
            # When leaving hybrid mode, reset original viewer to the working image
            if self._image_data is not None:
                self._viewer_orig.set_image(self._image_data.array)

        self._update_viewer_titles()

    def _on_params_changed(self) -> None:
        """Handle parameter changes from sidebar."""
        self._update_viewer_titles()

    def _update_viewer_titles(self) -> None:
        """Update Original and Image B titles depending on active mode and frequency assignment."""
        entry = self._sidebar.selected_feature
        if entry is not None and entry.group == "Hybrid":
            params = self._sidebar.current_params
            low_source = params.get("low_source", "")
            if "Image B (Low-pass)" in str(low_source):
                self._viewer_orig.set_title_base("Image A (High-pass)")
                self._viewer_img_b.set_title_base("Image B (Low-pass)")
            else:
                self._viewer_orig.set_title_base("Image A (Low-pass)")
                self._viewer_img_b.set_title_base("Image B (High-pass)")
        else:
            self._viewer_orig.set_title_base("Original")
            self._viewer_img_b.set_title_base("Image B")

    def _on_apply_feature(self) -> None:
        """Execute currently selected feature with current parameters.

        IMPORTANT: this method NEVER touches self._viewer_orig in normal modes.
        The Original panel is only changed by _load_image_file and _on_commit_result.
        In Hybrid mode, the modified versions of Image A and Image B are displayed
        in their respective windows as live previews.
        """
        if self._image_data is None:
            show_error(UnsupportedImageError("Open an image first."), parent=self)
            return

        entry = self._sidebar.selected_feature
        if entry is None:
            return

        import time
        t0 = time.perf_counter()

        params = self._sidebar.current_params

        output: FeatureOutput | None = run_safely(
            run_feature,
            entry,
            self._image_data,
            params,
            self._second_image_data,
            parent=self,
        )

        elapsed = time.perf_counter() - t0

        if output is None:
            self._completion_badge.setText("❌ Failed")
            self._completion_badge.setStyleSheet("""
                background-color: #f38ba8; color: #11111b; font-weight: bold;
                font-size: 11px; padding: 2px 10px; border-radius: 4px;
            """)
            self._completion_badge.setVisible(True)
            return

        self._last_result = output.result
        self._last_extras = output.extras

        # In Hybrid mode, display the modified previews in Image A and Image B windows
        if entry.group == "Hybrid":
            if "modified_a" in output.extras:
                self._viewer_orig.set_image(output.extras["modified_a"])
            if "modified_b" in output.extras:
                self._viewer_img_b.set_image(output.extras["modified_b"])

        # Update Result View only
        self._update_result_display()

        # Update Analysis Panel
        self._analysis_panel.set_result(output.result, output.extras)

        # Notify user that the operation has finished
        feature_name = entry.name
        self._completion_badge.setText(f"[DONE] {feature_name} finished ({elapsed:.2f}s)")
        self._completion_badge.setStyleSheet("""
            background-color: #a6e3a1; color: #11111b; font-weight: bold;
            font-size: 11px; padding: 2px 10px; border-radius: 4px;
        """)
        self._completion_badge.setVisible(True)
        self._status.showMessage(f"Finished '{feature_name}' in {elapsed:.3f} s", 5000)

    def _update_result_display(self) -> None:
        """Render the result in either single view or 3-grid edge view."""
        if self._last_result is None:
            return

        entry = self._sidebar.selected_feature
        is_edge = entry is not None and entry.group == "Edges" and entry.has_xy

        if is_edge and self._edge_view_mode == "all":
            # Display combined result in main result viewer and open 3-grid external window
            self._result_stack.setCurrentIndex(0)
            self._viewer_result.set_title_base("Combined Magnitude")
            self._viewer_result.set_image(self._last_result)
            self._show_edge_grid_window()
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

    def _show_edge_grid_window(self) -> None:
        """Show the 3-grid (Gradient X, Gradient Y, Magnitude) in a separate floating window."""
        if self._edge_window is None:
            self._edge_window = QDialog(self)
            self._edge_window.setWindowTitle("Edge Detection - 3-Grid View (Gx, Gy, Magnitude)")
            self._edge_window.resize(1100, 420)
            win_layout = QHBoxLayout(self._edge_window)
            win_layout.setContentsMargins(8, 8, 8, 8)
            win_layout.setSpacing(6)

            self._edge_win_gx = ImageViewer("Gradient X")
            self._edge_win_gy = ImageViewer("Gradient Y")
            self._edge_win_mag = ImageViewer("Combined Magnitude")

            win_layout.addWidget(self._edge_win_gx)
            win_layout.addWidget(self._edge_win_gy)
            win_layout.addWidget(self._edge_win_mag)

        # Update viewer images
        if "gx" in self._last_extras and self._edge_win_gx:
            self._edge_win_gx.set_image(self._last_extras["gx"])
        if "gy" in self._last_extras and self._edge_win_gy:
            self._edge_win_gy.set_image(self._last_extras["gy"])
        if self._last_result is not None and self._edge_win_mag:
            self._edge_win_mag.set_image(self._last_result)

        self._edge_window.show()
        self._edge_window.raise_()
        self._edge_window.activateWindow()

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
        """Use result as new input (Ctrl+U) to chain operations.

        The Original panel is updated to the new working image.
        The very first loaded image (_first_image_data) is preserved for Reset.
        """
        if self._last_result is None:
            show_error(Exception("No result to use. Apply an operation first."), parent=self)
            return

        # Wrap result in ImageData
        new_data = ImageData.from_array(self._last_result, self._original_path)
        self._image_data = new_data

        # Update History
        entry = self._sidebar.selected_feature
        name = entry.name if entry else "Operation"
        self._history.append(name)

        # Update Original panel to the committed image, clear Result
        self._viewer_orig.set_image(new_data.array)
        self._viewer_result.clear()
        self._last_result = None
        self._last_extras = {}

        self._sidebar.set_history(self._history)
        self._analysis_panel.set_original(new_data)
        self._update_status()

    def _on_reset_original(self) -> None:
        """Reload the VERY FIRST loaded image and reset the entire pipeline."""
        if self._first_image_data is None:
            if self._original_path is None:
                show_error(Exception("No original image to reset to."), parent=self)
                return
            # Fall back to reloading from disk if _first_image_data is somehow None
            self._load_image_file(self._original_path, self._read_as_gray)
            return

        # Restore state to the very first loaded image without disk I/O
        self._image_data = self._first_image_data
        self._history = ["Original"]
        self._last_result = None
        self._last_extras = {}

        self._viewer_orig.set_image(self._first_image_data.array)
        self._viewer_result.clear()
        self._viewer_gx.clear()
        self._viewer_gy.clear()
        self._viewer_mag.clear()

        # If Image B is loaded, also restore Image B to its original array
        if self._second_image_data is not None and self._viewer_img_b.isVisible():
            self._viewer_img_b.set_image(self._second_image_data.array)

        self._analysis_panel.set_original(self._first_image_data)
        self._sidebar.set_history(self._history)
        self._update_status()

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
        # 1. Reload Image A (original image)
        if self._original_path:
            self._load_image_file(self._original_path, as_gray)

        # 2. Reload Image B (if a second image is currently loaded in Hybrid mode)
        if self._second_image_path:
            b_data = run_safely(ImageData.load, self._second_image_path, as_gray, parent=self)
            if b_data is not None:
                self._second_image_data = b_data
                self._sidebar.set_second_image(b_data)
                self._viewer_img_b.set_image(b_data.array)

        # If in Hybrid mode and both images are present, re-run preview
        entry = self._sidebar.selected_feature
        if entry is not None and entry.group == "Hybrid" and self._second_image_data is not None:
            self._on_apply_feature()

    # ------------------------------------------------------------------ Zoom & Pan Synchronization

    def _on_viewer_zoom_pan_changed(
        self, sender, zoom: float, h_ratio: float, v_ratio: float
    ) -> None:
        """Synchronize zoom and pan across visible viewers if link option is enabled."""
        if not self._link_zoom_check.isChecked():
            return
        viewers = [
            v for v in (self._viewer_orig, self._viewer_img_b, self._viewer_result)
            if v.isVisible() and v is not sender
        ]
        for v in viewers:
            v.sync_view(zoom, h_ratio, v_ratio)

    def _on_fit_all(self) -> None:
        """Reset zoom on all visible viewers to fit their windows."""
        for v in (self._viewer_orig, self._viewer_img_b, self._viewer_result):
            if v.isVisible():
                v._reset_zoom()

    def showEvent(self, event) -> None:
        """Ensure splitter panes are evenly distributed when the window is first displayed."""
        super().showEvent(event)
        self._update_images_splitter_sizes()

    def _update_images_splitter_sizes(self) -> None:
        """Keep viewers in the row equal in width."""
        self._images_splitter.setChildrenCollapsible(False)
        total_w = self._images_splitter.width()
        if total_w < 100:
            total_w = max(1000, self.width() - 360)
        if not self._viewer_img_b.isHidden():
            third = max(1, total_w // 3)
            self._images_splitter.setSizes([third, third, third])
        else:
            half = max(1, total_w // 2)
            self._images_splitter.setSizes([half, 0, half])

    # ------------------------------------------------------------------ Status Bar

    def _update_status(self) -> None:
        """Update status bar information."""
        parts = []
        if self._image_data:
            if self._original_path:
                parts.append(Path(self._original_path).name)
            h, w = self._image_data.shape[:2]
            parts.append(f"{w}x{h}")
            parts.append("Gray" if self._image_data.is_gray else "RGB")
        if self._history:
            parts.append(" > ".join(self._history))
        self._status.showMessage(
            "   |   ".join(parts)
            if parts
            else "No image loaded - Open an image or drag & drop to begin"
        )
