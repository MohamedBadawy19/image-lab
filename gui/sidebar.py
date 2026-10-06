"""Studio Left Sidebar — unified feature selection, parameter controls, and actions.

The sidebar builds its feature picker entirely from CATALOG in gui/features.py,
ensuring that no feature names or parameter keys are hardcoded. It emits Qt signals
for all user actions and never touches the core modules directly.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        # Scroll area container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(12)
        self._layout.setContentsMargins(8, 8, 8, 8)

        # 1. Upload & Mode section
        self._setup_upload_section()

        # 2. Second Image slot (Hybrid only)
        self._setup_second_image_section()

        # 3. Feature Picker accordion
        self._setup_feature_picker()

        # 4. Parameters section
        self._setup_params_section()

        # 5. Actions & Buttons
        self._setup_actions_section()

        # 6. History line
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

        self._btn_open = QPushButton("📂 Open Image")
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
        """Create the second image slot for Hybrid feature."""
        self._second_img_group = QGroupBox("Second Image (Hybrid B)")
        layout = QVBoxLayout()

        self._btn_load_second = QPushButton("🖼️ Load Second Image")
        self._btn_load_second.clicked.connect(self.second_image_requested.emit)
        layout.addWidget(self._btn_load_second)

        self._second_img_thumb = ImageViewer("Image B")
        self._second_img_thumb.setFixedHeight(140)
        layout.addWidget(self._second_img_thumb)

        self._second_img_group.setLayout(layout)
        self._second_img_group.setVisible(False)
        self._layout.addWidget(self._second_img_group)

    def _setup_feature_picker(self) -> None:
        """Build the radio-button feature picker dynamically from CATALOG."""
        group = QGroupBox("Feature Picker")
        layout = QVBoxLayout()
        layout.setSpacing(6)

        for group_name, entries in CATALOG.items():
            sub_group = QGroupBox(group_name)
            sub_layout = QVBoxLayout()
            sub_layout.setContentsMargins(6, 6, 6, 6)
            sub_layout.setSpacing(4)

            for entry in entries:
                radio = QRadioButton(entry.name)
                self._button_group.addButton(radio)
                self._radio_to_entry[radio] = entry
                radio.toggled.connect(self._on_radio_toggled)
                sub_layout.addWidget(radio)

            sub_group.setLayout(sub_layout)
            layout.addWidget(sub_group)

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
        edge_layout.setContentsMargins(4, 4, 4, 4)

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
        layout.setSpacing(6)

        self._btn_apply = QPushButton("⚡ Apply")
        self._btn_apply.setFixedHeight(36)
        self._btn_apply.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: bold; font-size: 13px;"
        )
        self._btn_apply.clicked.connect(self.apply_requested.emit)
        layout.addWidget(self._btn_apply)

        self._live_check = QCheckBox("Live preview")
        self._live_check.setChecked(False)
        layout.addWidget(self._live_check)

        self._btn_commit = QPushButton("🔄 Use result as new input")
        self._btn_commit.clicked.connect(self.commit_requested.emit)
        layout.addWidget(self._btn_commit)

        row = QHBoxLayout()
        self._btn_reset = QPushButton("↺ Reset")
        self._btn_reset.clicked.connect(self.reset_requested.emit)
        row.addWidget(self._btn_reset)

        self._btn_save = QPushButton("💾 Save result")
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
        self._live_check.setEnabled(enabled)

    # ------------------------------------------------------------------ Internal Slots

    def _select_first_feature(self) -> None:
        """Select the first feature by default."""
        for radio, entry in self._radio_to_entry.items():
            radio.setChecked(True)
            self._update_selected_feature(entry)
            break

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

        # Update params panel
        self._param_panel.set_schema(entry.params_schema)

        # Show/hide second image slot
        self._second_img_group.setVisible(entry.needs_second_image)

        # Show/hide edge view options
        self._edge_view_group.setVisible(entry.group == "Edges" and entry.has_xy)

        self.feature_selected.emit(entry)

    def _on_mode_toggled(self, checked: bool) -> None:
        self._mode_btn.setText("Read mode: Gray" if checked else "Read mode: RGB")
        self.read_mode_toggled.emit(checked)

    def _on_params_changed(self) -> None:
        self.params_changed.emit()
        if self._live_check.isChecked():
            self.apply_requested.emit()

    def _set_edge_mode(self, mode: str) -> None:
        self.edge_view_changed.emit(mode)
