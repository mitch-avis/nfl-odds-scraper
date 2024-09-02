"""OddsScraper is a simple web scraper for NFL odds."""

import configparser
import re
import sys
import threading
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from odds_scraper.utils.logger import log

config = configparser.ConfigParser()
config.read("config.ini")

WEB_URL = config["DEFAULT"]["WebUrl"]
TIMEOUT = int(config["DEFAULT"]["Timeout"])
OUTPUT_PATH = Path(config["DEFAULT"]["OutputPath"])

WINDOW_WIDTH = 300
WINDOW_HEIGHT = 200
LOCAL_THREAD = threading.local()


class ScraperWorker(QThread):
    """Worker thread for scraping NFL odds."""

    finished = pyqtSignal()
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, start_week, end_week, driver):
        super().__init__()
        self.start_week = start_week
        self.end_week = end_week
        self.driver = driver
        self.scraping_active = True

    def run(self):
        """Scrapes NFL odds for the specified weeks."""
        try:
            for week in range(self.start_week, self.end_week + 1):
                if not self.scraping_active:
                    self.progress.emit("Scraping stopped by user.")
                    break
                self.driver.get(f"{WEB_URL}-{week}")
                WebDriverWait(self.driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                soup = BeautifulSoup(self.driver.page_source, "lxml")
                tables = soup.find_all("table")

                dataframes = []
                for table in tables:
                    table_data = pd.read_html(StringIO(str(table)))[0]
                    table_data.columns = ["Matchup"] + list(table_data.columns[1:])
                    dataframes.append(table_data)

                all_odds = pd.concat(dataframes, ignore_index=True)
                all_odds["Matchup"] = all_odds["Matchup"].apply(
                    lambda x: re.sub(r"^\d{1,2}:\d{2}[AP]M\w{2,3}\s*", "", x)
                )
                all_odds["Spread"] = all_odds["Spread"].apply(
                    lambda x: (
                        re.search(r"[-+]?\d+(\.\d+)?", x).group()
                        if re.search(r"[-+]?\d+(\.\d+)?", x)
                        else x
                    )
                )
                all_odds["Total"] = all_odds["Total"].apply(
                    lambda x: (
                        re.search(r"\d+(\.\d+)?", x).group() if re.search(r"\d+(\.\d+)?", x) else x
                    )
                )
                all_odds["Moneyline"] = all_odds["Moneyline"].apply(lambda x: x.replace("−", "-"))
                all_odds["Spread"] = pd.to_numeric(all_odds["Spread"])
                all_odds["Total"] = pd.to_numeric(all_odds["Total"])
                all_odds["Moneyline"] = pd.to_numeric(all_odds["Moneyline"])

                current_year = datetime.now().year
                output_file = Path(f"{OUTPUT_PATH}/{current_year-2000:02}{week:02}.xlsx")
                output_file.parent.mkdir(exist_ok=True, parents=True)
                with pd.ExcelWriter(output_file) as writer:
                    all_odds.to_excel(writer, index=False)
                self.progress.emit(f"Week {week} data scraped successfully.")
        except (ValueError, WebDriverException) as error:
            self.error.emit(f"An error occurred: {error}")
        finally:
            self.finished.emit()

    def stop(self):
        """Stops the scraping process."""
        self.scraping_active = False


class OddsScraperWindow(QtWidgets.QMainWindow):
    """OddsScraper's main window."""

    def __init__(self):
        """Initializes the main window."""
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
            driver = self.get_webdriver()
            start_week = int(self.start_week_edit.text())
            end_week = int(self.end_week_edit.text())

            self.worker = ScraperWorker(start_week, end_week, driver)
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

    def get_webdriver(self):
        """Initializes selenium web scraper."""
        driver = getattr(LOCAL_THREAD, "driver", None)
        if driver is None:
            options = FirefoxOptions()
            service = FirefoxService()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.set_preference("permissions.default.image", 2)  # Disable images
            options.set_preference("permissions.default.stylesheet", 2)  # Disable CSS
            options.set_preference(
                "general.useragent.override",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/58.0.3029.110 Safari/537.3",
            )
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(TIMEOUT)
            driver.implicitly_wait(TIMEOUT)
            LOCAL_THREAD.driver = driver
        return driver

    def stop_webdriver(self, driver):
        """Shuts down selenium web scraper."""
        if driver:
            driver.quit()
            LOCAL_THREAD.driver = None


def main():
    """Main function."""
    app = QtWidgets.QApplication([])
    window = OddsScraperWindow()
    window.show()
    app.aboutToQuit.connect(lambda: window.stop_webdriver(getattr(LOCAL_THREAD, "driver", None)))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
