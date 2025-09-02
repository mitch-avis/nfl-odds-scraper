"""Main entry point for the NFL Odds Scraper application."""

import sys

from PyQt6 import QtWidgets

from gui import OddsScraperWindow


def main():
    """Initializes and starts the application."""
    app = QtWidgets.QApplication(sys.argv)
    window = OddsScraperWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
