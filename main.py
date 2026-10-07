"""Entry point – run with: python main.py"""
import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Image Lab")
    app.setOrganizationName("CV Task 1")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
