"""Main entry point for the NFL Odds Scraper application."""

import sys
import traceback

from PyQt6 import QtWidgets

from gui import OddsScraperWindow
from utils.logger import log


def main():
    """Initializes and starts the application."""

    # Ensure uncaught exceptions get logged to file/console
    def _excepthook(exc_type, exc, traceback_object):
        try:
            log.error("Uncaught exception: %s: %s", exc_type.__name__, exc)
            log.debug(
                "Traceback:\n%s",
                "".join(traceback.format_exception(exc_type, exc, traceback_object)),
            )
        finally:
            # Show a minimal message box for user feedback in GUI mode
            try:
                QtWidgets.QMessageBox.critical(
                    None,
                    "NFL Odds Scraper - Error",
                    f"An unexpected error occurred:\n{exc_type.__name__}: {exc}\n",
                )
            except Exception:  # pylint: disable=broad-except
                # Catching Exception to suppress all errors in showing the error dialog (e.g.,
                # if QApplication is not initialized)
                pass

    sys.excepthook = _excepthook

    app = QtWidgets.QApplication(sys.argv)
    window = OddsScraperWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
