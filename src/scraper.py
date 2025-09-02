"""This module contains the ScraperWorker class for scraping NFL odds using Selenium."""

import re
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from constants import OUTPUT_PATH, TEAM_MAPPING, TIMEOUT, WEB_URL
from utils.logger import log


class ScraperWorker(QThread):
    """Worker thread for scraping NFL odds."""

    finished = pyqtSignal()
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, start_week, end_week):
        super().__init__()
        self.start_week = start_week
        self.end_week = end_week
        self.scraping_active = True
        self.driver = self.get_webdriver()

    def run(self):
        """Scrapes NFL odds for the specified weeks."""
        try:
            for week in range(self.start_week, self.end_week + 1):
                if not self.scraping_active:
                    self.progress.emit("Scraping stopped by user.")
                    break
                current_year = datetime.now().year
                self.driver.get(f"{WEB_URL}/?Year={current_year}&Week={week}")
                WebDriverWait(self.driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                soup = BeautifulSoup(self.driver.page_source, "lxml")
                tables = soup.find_all("table")
                all_odds = pd.read_html(StringIO(str(tables)))[1]
                all_odds.columns = ["Time", "Team", "Spread", "Moneyline", "Total"]
                all_odds["Team"] = all_odds["Team"].replace(TEAM_MAPPING)
                all_odds = all_odds[
                    ~all_odds.apply(
                        lambda row: row.astype(str).str.contains("Spread|Moneyline|Total").any(),
                        axis=1,
                    )
                ]
                all_odds["Spread"] = all_odds["Spread"].apply(lambda x: x.replace("−", "-"))
                all_odds["Moneyline"] = all_odds["Moneyline"].apply(lambda x: x.replace("−", "-"))
                all_odds["Total"] = all_odds["Total"].apply(lambda x: re.sub(r"[^\d.]", "", x))
                all_odds["Spread"] = pd.to_numeric(all_odds["Spread"], errors="coerce")
                all_odds["Moneyline"] = pd.to_numeric(all_odds["Moneyline"], errors="coerce")
                all_odds["Total"] = pd.to_numeric(all_odds["Total"], errors="coerce")

                output_file = Path(f"{OUTPUT_PATH}/{current_year-2000:02}{week:02}.xlsx")
                output_file.parent.mkdir(exist_ok=True, parents=True)
                with pd.ExcelWriter(output_file) as writer:
                    all_odds.to_excel(writer, index=False)
                self.progress.emit(f"Week {week} data scraped successfully.")
                log.info("Week %s data scraped successfully.", week)
        except (ValueError, WebDriverException) as error:
            self.error.emit(f"An error occurred: {error}")
            log.error("An error occurred: %s", error)
        finally:
            self.finished.emit()
            log.info("Scraping process finished.")
            self.driver.quit()

    def stop(self):
        """Stops the scraping process."""
        self.scraping_active = False

    def get_webdriver(self):
        """Initializes the Chrome web scraper using Selenium Manager."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        # Disable images and CSS for performance
        options.add_experimental_option(
            "prefs",
            {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.stylesheets": 2,
            },
        )
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # Selenium Manager handles ChromeDriver automatically
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(TIMEOUT)
        driver.implicitly_wait(TIMEOUT)
        return driver
