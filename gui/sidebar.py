"""Studio Left Sidebar - unified feature selection, parameter controls, and actions.

The sidebar builds its feature picker entirely from CATALOG in gui/features.py,
ensuring that no feature names or parameter keys are hardcoded. It emits Qt signals
for all user actions and never touches the core modules directly.

Features are directly selectable with 1-click, organized by clean flat category
dividers, with an optional category filter dropdown. The parameter panel explicitly
displays the name of the currently selected feature.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.image_data import ImageData
from gui.features import CATALOG, FeatureEntry
from gui.widgets import ImageViewer, ParamPanel


class Sidebar(QWidget):
    """Scrollable left sidebar containing upload, feature picker, parameters, and actions."""

    # Signals for MainWindow
    open_requested = Signal()
    second_image_requested = Signal()
    read_mode_toggled = Signal(bool)  # True = Gray, False = RGB
    feature_selected = Signal(object)  # FeatureEntry
    apply_requested = Signal()
    commit_requested = Signal()  # Use result as new input
    reset_requested = Signal()
    save_requested = Signal()
    edge_view_changed = Signal(str)  # "combined" | "gx" | "gy" | "all"
    params_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(330)

        # State
        self._current_feature: FeatureEntry | None = None
        self._radio_to_entry: dict[QRadioButton, FeatureEntry] = {}
        self._category_widgets: dict[str, QWidget] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        # Scroll area container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(8, 8, 8, 8)

        # 1. Upload & Mode section
        self._setup_upload_section()

        # 2. Second Image slot (Hybrid only)
        self._setup_second_image_section()

        # 3. Feature Picker with clean flat categories
        self._setup_feature_picker()

        # 4. Parameters section
        self._setup_params_section()

        # 5. Actions & Buttons
        self._setup_actions_section()

        # 6. History breadcrumb
        self._history_label = QLabel("Original")
        self._history_label.setWordWrap(True)
        self._history_label.setStyleSheet("color: #a6adc8; font-size: 11px; padding: 4px;")
        self._layout.addWidget(self._history_label)

        self._layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # Initial state: select first feature, disable until image loaded
        self._select_first_feature()
        self.set_controls_enabled(False)

    # ------------------------------------------------------------------ UI Setup

    def _setup_upload_section(self) -> None:
        """Create the open image button and RGB/Gray mode toggle."""
        group = QGroupBox("Input Image")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(6)

        self._btn_open = QPushButton("Open Image")
        self._btn_open.setFixedHeight(34)
        self._btn_open.setStyleSheet("font-weight: bold; font-size: 12px;")
        self._btn_open.clicked.connect(self.open_requested.emit)
        layout.addWidget(self._btn_open)

        # Read mode toggle
        self._mode_btn = QToolButton()
        self._mode_btn.setText("Read mode: RGB")
        self._mode_btn.setCheckable(True)
        self._mode_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._mode_btn.toggled.connect(self._on_mode_toggled)
        layout.addWidget(self._mode_btn)

        group.setLayout(layout)
        self._layout.addWidget(group)

    def _setup_second_image_section(self) -> None:
        """Create the second image slot for Hybrid feature with swap controls."""
        self._second_img_group = QGroupBox("Hybrid Source Controls")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(6)

        # Dynamic info label explaining which image is low-pass and which is high-pass
        self._hybrid_role_label = QLabel("Low-pass: Image A (Original)  |  High-pass: Image B (Second)")
        self._hybrid_role_label.setStyleSheet("color: #89b4fa; font-size: 11px; font-weight: bold;")
        self._hybrid_role_label.setWordWrap(True)
        layout.addWidget(self._hybrid_role_label)

        btn_row = QHBoxLayout()
        self._btn_load_second = QPushButton("Load Image B")
        self._btn_load_second.clicked.connect(self.second_image_requested.emit)
        btn_row.addWidget(self._btn_load_second)

        self._btn_swap_roles = QPushButton("Swap Roles (A ↔ B)")
        self._btn_swap_roles.setToolTip("Swap which image is Low-pass and which is High-pass")
        self._btn_swap_roles.clicked.connect(self._on_swap_hybrid_roles)
        btn_row.addWidget(self._btn_swap_roles)
        layout.addLayout(btn_row)

        self._second_img_thumb = ImageViewer("Image B Preview")
        self._second_img_thumb.setFixedHeight(120)
        layout.addWidget(self._second_img_thumb)

        self._second_img_group.setLayout(layout)
        self._second_img_group.setVisible(False)
        self._layout.addWidget(self._second_img_group)

    def _setup_feature_picker(self) -> None:
        """Build the feature picker dynamically from CATALOG using clean flat sections."""
        group = QGroupBox("Features")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(4)

        # Category filter dropdown
        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Filter:")
        filter_lbl.setStyleSheet("color: #a6adc8; font-size: 11px; font-weight: bold;")
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("All Categories")
        for group_name in CATALOG.keys():
            self._cat_combo.addItem(group_name)
        self._cat_combo.currentTextChanged.connect(self._on_category_filter_changed)
        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self._cat_combo, 1)
        layout.addLayout(filter_row)

        self._category_widgets = {}

        for group_name, entries in CATALOG.items():
            cat_widget = QWidget()
            cat_layout = QVBoxLayout(cat_widget)
            cat_layout.setContentsMargins(0, 4, 0, 4)
            cat_layout.setSpacing(3)

            # Flat section header (replaces nested QGroupBox so zero border overlap)
            header = QLabel(f"── {group_name.upper()} ──")
            header.setStyleSheet(
                "color: #89b4fa; font-weight: bold; font-size: 11px; "
                "letter-spacing: 0.5px; padding-top: 6px; padding-bottom: 2px;"
            )
            cat_layout.addWidget(header)

            for entry in entries:
                radio = QRadioButton(entry.name)
                radio.setStyleSheet("""
                    QRadioButton {
                        color: #cdd6f4;
                        font-size: 11px;
                        padding: 3px 6px;
                    }
                    QRadioButton:hover {
                        color: #89b4fa;
                    }
                """)
                self._button_group.addButton(radio)
                self._radio_to_entry[radio] = entry
                radio.toggled.connect(self._on_radio_toggled)
                cat_layout.addWidget(radio)

            layout.addWidget(cat_widget)
            self._category_widgets[group_name] = cat_widget

        group.setLayout(layout)
        self._layout.addWidget(group)

    def _setup_params_section(self) -> None:
        """Create the dynamic parameter panel and edge view selector."""
        self._param_panel = ParamPanel()
        self._param_panel.changed.connect(self._on_params_changed)
        self._layout.addWidget(self._param_panel)

        # Edge view toggle (X / Y / Combined / 3-grid)
        self._edge_view_group = QGroupBox("Edge View Mode")
        edge_layout = QHBoxLayout()
        edge_layout.setContentsMargins(8, 14, 8, 8)

        self._btn_view_comb = QPushButton("Combined")
        self._btn_view_comb.setCheckable(True)
        self._btn_view_comb.setChecked(True)
        self._btn_view_comb.clicked.connect(lambda: self._set_edge_mode("combined"))

        self._btn_view_x = QPushButton("X")
        self._btn_view_x.setCheckable(True)
        self._btn_view_x.clicked.connect(lambda: self._set_edge_mode("gx"))

        self._btn_view_y = QPushButton("Y")
        self._btn_view_y.setCheckable(True)
        self._btn_view_y.clicked.connect(lambda: self._set_edge_mode("gy"))

        self._btn_view_all = QPushButton("3-Grid")
        self._btn_view_all.setCheckable(True)
        self._btn_view_all.clicked.connect(lambda: self._set_edge_mode("all"))

        self._edge_btn_group = QButtonGroup(self)
        self._edge_btn_group.setExclusive(True)
        for b in (self._btn_view_comb, self._btn_view_x, self._btn_view_y, self._btn_view_all):
            self._edge_btn_group.addButton(b)
            edge_layout.addWidget(b)

        self._edge_view_group.setLayout(edge_layout)
        self._edge_view_group.setVisible(False)
        self._layout.addWidget(self._edge_view_group)

    def _setup_actions_section(self) -> None:
        """Create Apply, Live preview, Use as input, Reset, Save buttons."""
        group = QGroupBox("Actions")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(6)

        self._btn_apply = QPushButton("Apply")
        self._btn_apply.setFixedHeight(36)
        self._btn_apply.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; font-size: 13px;"
        )
        self._btn_apply.clicked.connect(self.apply_requested.emit)
        layout.addWidget(self._btn_apply)

        self._live_check = QCheckBox("Live preview")
        self._live_check.setChecked(False)
        layout.addWidget(self._live_check)

        self._btn_commit = QPushButton("Use result as new input  (Ctrl+U)")
        self._btn_commit.clicked.connect(self.commit_requested.emit)
        layout.addWidget(self._btn_commit)

        row = QHBoxLayout()
        self._btn_reset = QPushButton("Reset  (Ctrl+R)")
        self._btn_reset.clicked.connect(self.reset_requested.emit)
        row.addWidget(self._btn_reset)

        self._btn_save = QPushButton("Save result  (Ctrl+S)")
        self._btn_save.clicked.connect(self.save_requested.emit)
        row.addWidget(self._btn_save)
        layout.addLayout(row)

        group.setLayout(layout)
        self._layout.addWidget(group)

    # ------------------------------------------------------------------ Public API

    @property
    def selected_feature(self) -> FeatureEntry | None:
        return self._current_feature

    @property
    def current_params(self) -> dict:
        return self._param_panel.values()

    @property
    def is_live_preview(self) -> bool:
        return self._live_check.isChecked()

    def set_second_image(self, image_data: ImageData | None) -> None:
        """Update thumbnail in the second image slot."""
        if image_data is not None:
            self._second_img_thumb.set_image(image_data.array)
        else:
            self._second_img_thumb.clear()

    def set_history(self, history: list[str]) -> None:
        """Update history label display."""
        self._history_label.setText(" > ".join(history) if history else "Original")

    def set_read_mode(self, as_gray: bool) -> None:
        """Update read mode button state."""
        self._mode_btn.blockSignals(True)
        self._mode_btn.setChecked(as_gray)
        self._mode_btn.setText("Read mode: Gray" if as_gray else "Read mode: RGB")
        self._mode_btn.blockSignals(False)

    def set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable interactive widgets when an image is loaded or unloaded."""
        self._btn_apply.setEnabled(enabled)
        self._btn_commit.setEnabled(enabled)
        self._btn_reset.setEnabled(enabled)
        self._btn_save.setEnabled(enabled)
        self._btn_load_second.setEnabled(enabled)
        self._btn_swap_roles.setEnabled(enabled)
        self._live_check.setEnabled(enabled)

    # ------------------------------------------------------------------ Internal Slots

    def _select_first_feature(self) -> None:
        """Select the first feature by default."""
        for radio, entry in self._radio_to_entry.items():
            radio.setChecked(True)
            self._update_selected_feature(entry)
            break

    def _on_category_filter_changed(self, category: str) -> None:
        """Filter visible categories by dropdown selection."""
        for group_name, widget in self._category_widgets.items():
            if category == "All Categories" or category == group_name:
                widget.show()
            else:
                widget.hide()

    def _on_radio_toggled(self, checked: bool) -> None:
        """Handle feature radio button toggling."""
        if not checked:
            return
        radio = self.sender()
        entry = self._radio_to_entry.get(radio)
        if entry:
            self._update_selected_feature(entry)

    def _update_selected_feature(self, entry: FeatureEntry) -> None:
        """Reconfigure UI components for the newly selected feature."""
        self._current_feature = entry

        # Update params panel with feature name and schema
        self._param_panel.set_feature(entry.name, entry.params_schema)

        # Show/hide second image slot
        self._second_img_group.setVisible(entry.needs_second_image)
        if entry.needs_second_image:
            self._update_hybrid_role_label()

        # Show/hide edge view options
        self._edge_view_group.setVisible(entry.group == "Edges" and entry.has_xy)

        self.feature_selected.emit(entry)

    def _on_swap_hybrid_roles(self) -> None:
        """Toggle low/high pass assignment in parameter panel."""
        combo = self._param_panel._controls.get("low_source")
        if combo is not None:
            new_idx = 1 if combo.currentIndex() == 0 else 0
            combo.setCurrentIndex(new_idx)
        self._update_hybrid_role_label()

    def _update_hybrid_role_label(self) -> None:
        """Keep the hybrid role label in sync with param panel selection."""
        if self._current_feature and self._current_feature.group == "Hybrid":
            vals = self._param_panel.values()
            low_source = vals.get("low_source", "")
            if "Image B (Low-pass)" in str(low_source):
                self._hybrid_role_label.setText("Low-pass: Image B (Second)  |  High-pass: Image A (Original)")
            else:
                self._hybrid_role_label.setText("Low-pass: Image A (Original)  |  High-pass: Image B (Second)")

    def _on_mode_toggled(self, checked: bool) -> None:
        self._mode_btn.setText("Read mode: Gray" if checked else "Read mode: RGB")
        self.read_mode_toggled.emit(checked)

    def _on_params_changed(self) -> None:
        self._update_hybrid_role_label()
        self.params_changed.emit()
        if self._live_check.isChecked():
            self.apply_requested.emit()

    def _set_edge_mode(self, mode: str) -> None:
        self.edge_view_changed.emit(mode)
