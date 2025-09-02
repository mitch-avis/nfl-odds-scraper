"""GUI module for the NFL Odds Scraper application."""

from PyQt6 import QtCore, QtWidgets
from selenium.common.exceptions import WebDriverException

from constants import WINDOW_HEIGHT, WINDOW_WIDTH
from scraper import ScraperWorker
from utils.logger import log


class OddsScraperWindow(QtWidgets.QMainWindow):
    """Main window for the NFL Odds Scraper GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFL Odds Scraper")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.general_layout = QtWidgets.QVBoxLayout()
        central_widget = QtWidgets.QWidget(self)
        central_widget.setLayout(self.general_layout)
        self.setCentralWidget(central_widget)
        self.create_interface()
        self.worker = None

    def create_interface(self):
        """Creates the basic interface."""
        grid_layout = QtWidgets.QGridLayout()

        intro_label = QtWidgets.QLabel("Enter Start Week and End Week to scrape odds:")
        intro_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        start_week_label = QtWidgets.QLabel("Start Week:")
        end_week_label = QtWidgets.QLabel("End Week:")
        self.status_text = QtWidgets.QLabel("Ready")

        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setAutoDefault(True)
        self.start_button.clicked.connect(self.start_scraping)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setAutoDefault(True)
        self.stop_button.clicked.connect(self.stop_scraping)
        self.stop_button.setEnabled(False)

        self.start_week_edit = QtWidgets.QLineEdit()
        self.start_week_edit.setMaxLength(2)
        self.start_week_edit.setFixedWidth(30)
        self.start_week_edit.returnPressed.connect(self.start_button.click)

        self.end_week_edit = QtWidgets.QLineEdit()
        self.end_week_edit.setMaxLength(2)
        self.end_week_edit.setFixedWidth(30)
        self.end_week_edit.returnPressed.connect(self.start_button.click)

        grid_layout.addWidget(intro_label, 0, 0, 1, 3)
        grid_layout.addWidget(start_week_label, 1, 0)
        grid_layout.addWidget(self.start_week_edit, 1, 1)
        grid_layout.addWidget(end_week_label, 2, 0)
        grid_layout.addWidget(self.end_week_edit, 2, 1)
        grid_layout.addWidget(self.start_button, 3, 0)
        grid_layout.addWidget(self.stop_button, 3, 2)
        grid_layout.addWidget(self.status_text, 4, 0, 1, 3)

        self.general_layout.addLayout(grid_layout)

    def start_scraping(self):
        """Starts the scraping process in a separate thread."""
        self.start_button.setEnabled(False)
        self.status_text.setText("Running...")
        self.status_text.repaint()

        if not self.validate_inputs():
            self.start_button.setEnabled(True)
            return

        try:
            start_week = int(self.start_week_edit.text())
            end_week = int(self.end_week_edit.text())

            self.worker = ScraperWorker(start_week, end_week)
            self.worker.finished.connect(self.on_finished)
            self.worker.progress.connect(self.on_progress)
            self.worker.error.connect(self.on_error)
            self.worker.start()
            self.stop_button.setEnabled(True)
        except (ValueError, WebDriverException) as error:
            log.error("An error occurred: %s", error)
            self.status_text.setText("An error occurred. Check logs for details.")
            self.start_button.setEnabled(True)

    def stop_scraping(self):
        """Stops the scraping process."""
        if self.worker:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.status_text.setText("Stopping...")
            self.status_text.repaint()

    def on_finished(self):
        """Handles the completion of the scraping process."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_text.setText("Done!")
        self.status_text.repaint()

    def on_progress(self, message):
        """Updates the status text with progress messages."""
        self.status_text.setText(message)
        self.status_text.repaint()

    def on_error(self, message):
        """Handles errors during the scraping process."""
        self.status_text.setText(message)
        self.status_text.repaint()

    def validate_inputs(self):
        """Validates the start week and end week inputs."""

        def validate_week(week_str, label):
            try:
                week = int(week_str)
                if week < 1 or week > 18:
                    return f"{label} must be between 1 and 18."
            except ValueError:
                return f"{label} must be a number between 1 and 18."
            return None

        start_week_error = validate_week(self.start_week_edit.text(), "Start week")
        if start_week_error:
            self.status_text.setText(start_week_error)
            return False

        end_week_error = validate_week(self.end_week_edit.text(), "End week")
        if end_week_error:
            self.status_text.setText(end_week_error)
            return False

        if int(self.end_week_edit.text()) < int(self.start_week_edit.text()):
            self.status_text.setText("End week must be greater than or equal to start week.")
            return False

        return True
