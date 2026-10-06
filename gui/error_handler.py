"""Central error handler — the ONE place errors are shown to the user.

Every GUI action must route through run_safely() so that exceptions are caught,
logged, and shown in a consistent way.
"""

import logging
import traceback

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from core.base import AppError

log = logging.getLogger(__name__)


def show_error(exception: BaseException, parent=None) -> None:
    """Display an error to the user and log the full traceback.

    - AppError subclasses   -> warning with the friendly message.
    - NotImplementedError   -> info box explaining a teammate hasn't finished yet.
    - Everything else       -> critical box with a generic message + details.
    """
    tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
    log.error("".join(tb))

    if isinstance(exception, AppError):
        QMessageBox.warning(parent, "Error", str(exception))
    elif isinstance(exception, NotImplementedError):
        QMessageBox.information(
            parent,
            "Not implemented",
            "This feature is not implemented yet (a teammate is still working on it).",
        )
    else:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unexpected error")
        box.setText("An unexpected error occurred.")
        box.setDetailedText("".join(tb))
        box.exec()


def run_safely(fn, *args, parent=None, **kwargs):
    """Run *fn* with a wait cursor, catch every exception, show it via show_error.

    Returns the result on success, None on failure.
    """
    try:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        result = fn(*args, **kwargs)
        return result
    except Exception as exc:
        show_error(exc, parent)
        return None
    finally:
        QApplication.restoreOverrideCursor()
