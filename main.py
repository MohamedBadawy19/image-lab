"""ImageLab entry point — PySide6 desktop application.

Sets up logging, applies the dark Fusion theme, installs a global
exception hook, and shows the main window.
"""

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from gui.error_handler import show_error


def _setup_logging() -> None:
    """Configure logging to file and stderr."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("image_lab.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _apply_dark_fusion(app: QApplication) -> None:
    """Apply the Fusion style with a dark colour palette and accent colour."""
    app.setStyle("Fusion")
    palette = QPalette()

    # Base colours
    dark = QColor(30, 30, 46)
    mid = QColor(49, 50, 68)
    light_text = QColor(205, 214, 244)
    accent = QColor(137, 180, 250)
    disabled = QColor(108, 112, 134)
    highlight = QColor(137, 180, 250)

    palette.setColor(QPalette.ColorRole.Window, dark)
    palette.setColor(QPalette.ColorRole.WindowText, light_text)
    palette.setColor(QPalette.ColorRole.Base, QColor(24, 24, 37))
    palette.setColor(QPalette.ColorRole.AlternateBase, mid)
    palette.setColor(QPalette.ColorRole.ToolTipBase, mid)
    palette.setColor(QPalette.ColorRole.ToolTipText, light_text)
    palette.setColor(QPalette.ColorRole.Text, light_text)
    palette.setColor(QPalette.ColorRole.Button, mid)
    palette.setColor(QPalette.ColorRole.ButtonText, light_text)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(17, 17, 27))

    # Disabled state
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)

    app.setPalette(palette)

    # Stylesheet tweaks for rounded panels and consistent spacing
    app.setStyleSheet("""
        QGroupBox {
            border: 1px solid #45475a;
            border-radius: 8px;
            margin-top: 1em;
            padding-top: 0.6em;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QPushButton {
            background-color: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 6px 14px;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #45475a;
        }
        QPushButton:pressed {
            background-color: #585b70;
        }
        QPushButton:disabled {
            color: #6c7086;
        }
        QTabWidget::pane {
            border: 1px solid #45475a;
            border-radius: 6px;
        }
        QTabBar::tab {
            background: #313244;
            border: 1px solid #45475a;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 6px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #1e1e2e;
            border-bottom: 2px solid #89b4fa;
        }
        QTabBar::tab:hover {
            background: #45475a;
        }
        QComboBox {
            border: 1px solid #45475a;
            border-radius: 4px;
            padding: 4px 8px;
            background: #313244;
        }
        QSlider::groove:horizontal {
            height: 4px;
            background: #45475a;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #89b4fa;
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QScrollArea {
            border: none;
        }
        QToolButton {
            background-color: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 6px 14px;
        }
        QToolButton:checked {
            background-color: #89b4fa;
            color: #11111b;
        }
        QToolButton:hover {
            background-color: #45475a;
        }
        """)


def _install_excepthook() -> None:
    """Install a global exception hook that routes to error_handler."""
    _original = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        show_error(exc_value)
        _original(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def main() -> None:
    """Application entry point."""
    _setup_logging()
    log = logging.getLogger("main")
    log.info("ImageLab starting")

    app = QApplication(sys.argv)
    _apply_dark_fusion(app)
    _install_excepthook()

    from gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    log.info("Window shown")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
