"""Studio Left Sidebar - unified feature selection, parameter controls, and actions.

The sidebar builds its feature picker entirely from CATALOG in gui/features.py,
ensuring that no feature names or parameter keys are hardcoded. It emits Qt signals
for all user actions and never touches the core modules directly.

Features are directly selectable with 1-click, organized by clean flat category
dividers, with an optional category filter dropdown.
Includes dedicated per-image collapsible control groups for Hybrid mode.
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
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.filters import FILTERS
from core.image_data import ImageData
from core.noise import NOISES
from gui.features import CATALOG, FeatureEntry
from gui.widgets import CollapsibleBox, JumpSlider, ParamPanel


class ImageControlWidget(QWidget):
    """Controls for a single hybrid image: role cutoff, independent filter & noise."""

    changed = Signal()

    def __init__(self, name: str, default_cutoff: int = 20, is_low: bool = True, parent=None):
        super().__init__(parent)
        self._name = name
        self._is_low = is_low

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # 1. Role Badge & Cutoff
        self._role_label = QLabel(f"Role: {'Low-pass' if is_low else 'High-pass'}")
        self._role_label.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._role_label)

        cutoff_box = QHBoxLayout()
        self._cutoff_title = QLabel("Cutoff (radius):")
        self._cutoff_title.setStyleSheet("font-size: 11px;")
        cutoff_box.addWidget(self._cutoff_title)

        self._cutoff_slider = JumpSlider(Qt.Orientation.Horizontal)
        self._cutoff_slider.setRange(1, 200)
        self._cutoff_slider.setValue(default_cutoff)

        self._cutoff_spin = QSpinBox()
        self._cutoff_spin.setRange(1, 200)
        self._cutoff_spin.setValue(default_cutoff)
        self._cutoff_spin.setStyleSheet("""
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

        self._cutoff_slider.valueChanged.connect(self._cutoff_spin.setValue)
        self._cutoff_spin.valueChanged.connect(self._cutoff_slider.setValue)
        self._cutoff_slider.valueChanged.connect(lambda: self.changed.emit())

        cutoff_box.addWidget(self._cutoff_slider)
        cutoff_box.addWidget(self._cutoff_spin)
        layout.addLayout(cutoff_box)

        # 2. Filter selection & parameters
        f_box = QHBoxLayout()
        f_lbl = QLabel("Filter:")
        f_lbl.setStyleSheet("font-size: 11px;")
        f_box.addWidget(f_lbl)

        self._filter_combo = QComboBox()
        self._filter_combo.addItem("None")
        for f_name in FILTERS.keys():
            self._filter_combo.addItem(f_name)
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)
        f_box.addWidget(self._filter_combo, 1)
        layout.addLayout(f_box)

        self._filter_params = ParamPanel()
        self._filter_params.setTitle("Filter Parameters")
        self._filter_params.changed.connect(self.changed.emit)
        self._filter_params.setVisible(False)
        layout.addWidget(self._filter_params)

        # 3. Noise selection & parameters
        n_box = QHBoxLayout()
        n_lbl = QLabel("Noise:")
        n_lbl.setStyleSheet("font-size: 11px;")
        n_box.addWidget(n_lbl)

        self._noise_combo = QComboBox()
        self._noise_combo.addItem("None")
        for n_name in NOISES.keys():
            self._noise_combo.addItem(n_name)
        self._noise_combo.currentTextChanged.connect(self._on_noise_changed)
        n_box.addWidget(self._noise_combo, 1)
        layout.addLayout(n_box)

        self._noise_params = ParamPanel()
        self._noise_params.setTitle("Noise Parameters")
        self._noise_params.changed.connect(self.changed.emit)
        self._noise_params.setVisible(False)
        layout.addWidget(self._noise_params)

    def set_role(self, is_low: bool) -> None:
        self._is_low = is_low
        role_str = "Low-pass" if is_low else "High-pass"
        self._role_label.setText(f"Role: {role_str}")
        self._cutoff_title.setText(f"{role_str} Cutoff:")

    def _on_filter_changed(self, text: str) -> None:
        if text == "None" or text not in FILTERS:
            self._filter_params.setVisible(False)
        else:
            cls = FILTERS[text]
            self._filter_params.set_schema(cls.params_schema)
            self._filter_params.setTitle(f"{text} Parameters")
            self._filter_params.setVisible(True)
        self.changed.emit()

    def _on_noise_changed(self, text: str) -> None:
        if text == "None" or text not in NOISES:
            self._noise_params.setVisible(False)
        else:
            cls = NOISES[text]
            self._noise_params.set_schema(cls.params_schema)
            self._noise_params.setTitle(f"{text} Parameters")
            self._noise_params.setVisible(True)
        self.changed.emit()

    def get_params(self) -> dict:
        f_text = self._filter_combo.currentText()
        n_text = self._noise_combo.currentText()
        return {
            "cutoff": self._cutoff_spin.value(),
            "filter": f_text,
            "filter_params": self._filter_params.values() if f_text != "None" else {},
            "noise": n_text,
            "noise_params": self._noise_params.values() if n_text != "None" else {},
        }


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
        self.setFixedWidth(340)

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

        # 2. Feature Picker with clean flat categories
        self._setup_feature_picker()

        # 3. Parameters section (standard modes)
        self._setup_params_section()

        # 4. Dedicated Hybrid Controls section (Image A & Image B collapsible groups)
        self._setup_hybrid_section()

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

            # Flat section header
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

    def _setup_hybrid_section(self) -> None:
        """Create dedicated hybrid controls with separate Image A and Image B collapsible groups."""
        self._hybrid_group = QGroupBox("Hybrid Image Controls")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(6)

        # 1. Load second image button + status
        b_row = QHBoxLayout()
        self._btn_load_second = QPushButton("Load Image B")
        self._btn_load_second.clicked.connect(self.second_image_requested.emit)
        self._img_b_status = QLabel("Image B: Not loaded")
        self._img_b_status.setStyleSheet("color: #a6adc8; font-size: 10px;")
        b_row.addWidget(self._btn_load_second)
        b_row.addWidget(self._img_b_status)
        layout.addLayout(b_row)

        # 2. Pass Assignment
        assign_lbl = QLabel("Pass Assignment:")
        assign_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(assign_lbl)

        self._hybrid_role_combo = QComboBox()
        self._hybrid_role_combo.addItem("Image A (Low-pass) + Image B (High-pass)")
        self._hybrid_role_combo.addItem("Image B (Low-pass) + Image A (High-pass)")
        self._hybrid_role_combo.currentIndexChanged.connect(self._on_hybrid_role_changed)
        layout.addWidget(self._hybrid_role_combo)

        # 3. Image A Collapsible Controls
        self._box_img_a = CollapsibleBox("Image A Controls", is_expanded=True)
        self._img_a_ctrl = ImageControlWidget(name="Image A", default_cutoff=20, is_low=True)
        self._img_a_ctrl.changed.connect(self._on_params_changed)
        self._box_img_a.content_layout.addWidget(self._img_a_ctrl)
        layout.addWidget(self._box_img_a)

        # 4. Image B Collapsible Controls
        self._box_img_b = CollapsibleBox("Image B Controls", is_expanded=True)
        self._img_b_ctrl = ImageControlWidget(name="Image B", default_cutoff=20, is_low=False)
        self._img_b_ctrl.changed.connect(self._on_params_changed)
        self._box_img_b.content_layout.addWidget(self._img_b_ctrl)
        layout.addWidget(self._box_img_b)

        self._hybrid_group.setLayout(layout)
        self._hybrid_group.setVisible(False)
        self._layout.addWidget(self._hybrid_group)

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
        if self._current_feature and self._current_feature.group == "Hybrid":
            return self._get_hybrid_params()
        return self._param_panel.values()

    @property
    def is_live_preview(self) -> bool:
        return self._live_check.isChecked()

    def set_second_image(self, image_data: ImageData | None) -> None:
        """Update second image status label."""
        if image_data is not None:
            h, w = image_data.shape[:2]
            mode = "Gray" if image_data.is_gray else "RGB"
            self._img_b_status.setText(f"Image B: {w}x{h} {mode}")
            self._img_b_status.setStyleSheet("color: #a6e3a1; font-size: 10px; font-weight: bold;")
        else:
            self._img_b_status.setText("Image B: Not loaded")
            self._img_b_status.setStyleSheet("color: #a6adc8; font-size: 10px;")

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
        is_hybrid = entry.group == "Hybrid"

        if is_hybrid:
            self._param_panel.setVisible(False)
            self._hybrid_group.setVisible(True)
        else:
            self._hybrid_group.setVisible(False)
            self._param_panel.setVisible(True)
            self._param_panel.set_feature(entry.name, entry.params_schema)

        # Show/hide edge view options
        self._edge_view_group.setVisible(entry.group == "Edges" and entry.has_xy)

        self.feature_selected.emit(entry)

    def _on_hybrid_role_changed(self, index: int) -> None:
        """Update role badges and cutoff titles in per-image controls."""
        is_a_low = (index == 0)
        self._img_a_ctrl.set_role(is_a_low)
        self._img_b_ctrl.set_role(not is_a_low)
        self._on_params_changed()

    def _get_hybrid_params(self) -> dict:
        """Assemble current parameters for Hybrid mode."""
        low_source = self._hybrid_role_combo.currentText()
        a = self._img_a_ctrl.get_params()
        b = self._img_b_ctrl.get_params()
        return {
            "low_source": low_source,
            "cutoff_a": a["cutoff"],
            "cutoff_b": b["cutoff"],
            "filter_a": a["filter"],
            "filter_params_a": a["filter_params"],
            "noise_a": a["noise"],
            "noise_params_a": a["noise_params"],
            "filter_b": b["filter"],
            "filter_params_b": b["filter_params"],
            "noise_b": b["noise"],
            "noise_params_b": b["noise_params"],
        }

    def _on_mode_toggled(self, checked: bool) -> None:
        self._mode_btn.setText("Read mode: Gray" if checked else "Read mode: RGB")
        self.read_mode_toggled.emit(checked)

    def _on_params_changed(self) -> None:
        self.params_changed.emit()
        if self._live_check.isChecked():
            self.apply_requested.emit()

    def _set_edge_mode(self, mode: str) -> None:
        self.edge_view_changed.emit(mode)
