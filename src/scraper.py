"""This module contains the ScraperWorker class for scraping NFL odds using Selenium."""

import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from constants import (
    DEFAULT_MONEYLINE,
    DEFAULT_SPREAD,
    DEFAULT_TOTAL,
    OUTPUT_PATH,
    TEAM_NICKNAME_TO_FULL,
    TIMEOUT,
    WEB_URL,
)
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
        """Scrapes NFL odds for the specified weeks.

        Per requirements:
        - Only Consensus column is used for Spread, Total, Moneyline.
        - Two rows per game (away and home), with the same Total per game.
        - Team names normalized using TEAM_NICKNAME_TO_FULL mapping.
        - Time normalized to Mountain Time (America/Denver).
        """
        try:
            # Navigate to base URL
            log.info("Loading base URL: %s", WEB_URL)
            self.driver.get(WEB_URL)

            for week in range(self.start_week, self.end_week + 1):
                if not self.scraping_active:
                    self.progress.emit("Scraping stopped by user.")
                    break

                current_year = datetime.now().year

                # Open week dropdown and select desired week
                log.info("Selecting Week %s via dropdown", week)
                self._select_week(week)

                log.debug("Building BeautifulSoup for Week %s", week)
                soup = BeautifulSoup(self.driver.page_source, "lxml")

                # Parse each market to find consensus column index
                tbody_spread = soup.find("tbody", id="odds-table-spread--0")
                tbody_total = soup.find("tbody", id="odds-table-total--0")
                tbody_money = soup.find("tbody", id="odds-table-moneyline--0")

                if not (tbody_spread and tbody_total and tbody_money):
                    raise ValueError("Could not locate one or more odds tables on the page.")

                spread_idx = self._find_consensus_index(tbody_spread)
                total_idx = self._find_consensus_index(tbody_total)
                money_idx = self._find_consensus_index(tbody_money)
                log.debug(
                    "Week %s: consensus indexes -> spread=%s total=%s moneyline=%s",
                    week,
                    spread_idx,
                    total_idx,
                    money_idx,
                )

                # Iterate games (4 rows per game: header/time, away, home, matchup)
                rows_spread = tbody_spread.find_all("tr", recursive=False)
                rows_total = tbody_total.find_all("tr", recursive=False)
                rows_money = tbody_money.find_all("tr", recursive=False)

                records = []
                i = 0
                while i + 2 < len(rows_spread):
                    time_row_spread = rows_spread[i]
                    away_row_spread = rows_spread[i + 1]
                    home_row_spread = rows_spread[i + 2]
                    # Corresponding rows for total/moneyline
                    # corresponding time rows not needed beyond synchronization
                    away_row_total = rows_total[i + 1]
                    home_row_total = rows_total[i + 2]
                    # corresponding time rows not needed beyond synchronization
                    away_row_money = rows_money[i + 1]
                    home_row_money = rows_money[i + 2]

                    # Parse time (from the time row in spread table) and normalize to MT
                    time_text = self._first_td_text(time_row_spread)
                    time_mt = self._to_mountain_time(time_text)

                    # Parse teams
                    away_team = self._parse_team_name(away_row_spread)
                    home_team = self._parse_team_name(home_row_spread)

                    # Parse consensus values
                    away_spread = self._parse_consensus_value(
                        away_row_spread,
                        spread_idx,
                        market="spread",
                    )
                    home_spread = self._parse_consensus_value(
                        home_row_spread,
                        spread_idx,
                        market="spread",
                    )

                    away_ml = self._parse_consensus_value(
                        away_row_money,
                        money_idx,
                        market="moneyline",
                    )
                    home_ml = self._parse_consensus_value(
                        home_row_money,
                        money_idx,
                        market="moneyline",
                    )

                    # Total: use a single numeric for the game; try away first, else home
                    total_away = self._parse_consensus_value(
                        away_row_total,
                        total_idx,
                        market="total",
                    )
                    total_home = self._parse_consensus_value(
                        home_row_total,
                        total_idx,
                        market="total",
                    )
                    game_total = total_away if total_away != "" else total_home

                    records.append(
                        {
                            "Time": time_mt,
                            "Team": away_team,
                            "Spread": away_spread,
                            "Moneyline": away_ml,
                            "Total": game_total,
                        }
                    )
                    records.append(
                        {
                            "Time": time_mt,
                            "Team": home_team,
                            "Spread": home_spread,
                            "Moneyline": home_ml,
                            "Total": game_total,
                        }
                    )

                    # advance by 4 rows for next game
                    i += 4

                log.info("Week %s: parsed %s rows (two per game)", week, len(records))
                all_odds = pd.DataFrame(
                    records,
                    columns=["Time", "Team", "Spread", "Moneyline", "Total"],
                )

                # Coerce numeric fields per spec
                all_odds["Spread"] = all_odds["Spread"].apply(self._to_float_or_blank)
                all_odds["Moneyline"] = all_odds["Moneyline"].apply(self._to_int_or_blank)
                all_odds["Total"] = all_odds["Total"].apply(self._to_float1_or_blank)

                # Save results per week
                output_file = Path(f"{OUTPUT_PATH}/{current_year-2000:02}{week:02}.xlsx")
                output_file.parent.mkdir(exist_ok=True, parents=True)
                with pd.ExcelWriter(output_file) as writer:
                    all_odds.to_excel(writer, index=False)

                self.progress.emit(f"Week {week} data scraped successfully.")
                log.info("Week %s data scraped successfully.", week)
        except (ValueError, WebDriverException, TimeoutException) as error:
            msg = getattr(error, "msg", None) or str(error)
            self.error.emit(f"An error occurred: {error.__class__.__name__}: {msg}")
            log.error("An error occurred: %s: %s", error.__class__.__name__, msg)
            log.debug("Traceback for error:\n%s", traceback.format_exc())
        finally:
            self.finished.emit()
            log.info("Scraping process finished.")
            try:
                self.driver.quit()
            except WebDriverException:  # pragma: no cover - defensive
                pass

    def stop(self):
        """Stops the scraping process."""
        self.scraping_active = False

    def get_webdriver(self):
        """Initializes the Chrome web scraper using Selenium Manager."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        # Make DOM available sooner; no need to wait for all subresources
        options.set_capability("pageLoadStrategy", "eager")
        # Reduce Chrome noise in console
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
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

        service = Service(log_path=("NUL" if os.name == "nt" else os.devnull))
        driver = webdriver.Chrome(options=options, service=service)
        driver.set_page_load_timeout(TIMEOUT)
        driver.implicitly_wait(TIMEOUT)
        # Block heavy third-party analytics/ads/fonts to speed up
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd(
                "Network.setBlockedURLs",
                {
                    "urls": [
                        "*googletagmanager.com*",
                        "*google-analytics.com*",
                        "*doubleclick.net*",
                        "*gstatic.com*",
                        "*fonts.googleapis.com*",
                        "*fonts.gstatic.com*",
                        "*cdn.cookielaw.org*",
                        "*onetrust*",
                        "*rudderlabs*",
                        "*facebook.com*",
                        "*twitter.com*",
                        "*bet-links.com*",
                        "*grammarly*",
                    ]
                },
            )
        except WebDriverException:
            pass
        return driver

    # -----------------------------
    # Helper methods
    # -----------------------------

    def _select_week(self, week: int):
        """Open the Week dropdown and select the desired week (Week N) robustly.

        Strategy:
        - Prefer stable CSS selectors over brittle absolute XPaths.
        - If the desired week is already selected, return early.
        - Click the week picker using JS click with retries to avoid intercepts.
        - Wait for the active menu to appear, then click the desired week.
        - Wait for either the header text to reflect the new week and the odds table to refresh
          (staleness of previous tbody), or fall back to direct navigation via the option's
          data-endpoint if UI interaction fails.
        """
        driver = self.driver

        # Locators
        week_picker_span_locator = (
            By.CSS_SELECTOR,
            ".filters-week-picker .week-picker-week > span[data-content='#week-picker-week']",
        )
        week_menu_locator = (By.ID, "week-picker-week")
        week_menu_active_locator = (
            By.CSS_SELECTOR,
            "ul#week-picker-week.menu.active",
        )
        # A table element to use for staleness detection
        table_locator = (By.CSS_SELECTOR, "tbody#odds-table-spread--0")

        wait = WebDriverWait(driver, TIMEOUT)

        # Early exit if already selected
        picker_span = wait.until(EC.presence_of_element_located(week_picker_span_locator))
        current_text = picker_span.text.strip()
        if current_text.lower().startswith("week ") and current_text.strip() == f"Week {week}":
            log.debug("Week %s already selected; skipping dropdown interaction", week)
            return

        # Capture existing table for staleness wait
        try:
            old_table = driver.find_element(*table_locator)
        except NoSuchElementException:
            old_table = None

        # Open the menu (retry a couple of times in case of intercepts)
        for attempt in range(3):
            try:
                wait.until(EC.element_to_be_clickable(week_picker_span_locator))
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    driver.find_element(*week_picker_span_locator),
                )
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(*week_picker_span_locator),
                )
                # Wait for menu to be visible and active
                wait.until(EC.visibility_of_element_located(week_menu_locator))
                try:
                    wait.until(EC.presence_of_element_located(week_menu_active_locator))
                except TimeoutException:
                    # Some builds don't toggle 'active' class; continue if visible
                    pass
                break
            except (
                ElementClickInterceptedException,
                StaleElementReferenceException,
                TimeoutException,
            ) as exception:
                log.debug("Attempt %s to open week menu failed: %s", attempt + 1, exception)
                if attempt == 2:
                    log.warning(
                        "Falling back to direct navigation for week %s (unable to open menu)",
                        week,
                    )
                else:
                    continue

        # Try clicking the desired week option; on failure, attempt direct navigation
        option_xpath = (
            f"//ul[@id='week-picker-week']//li[.//span[normalize-space() = 'Week {week}']]"
        )
        try:
            option_li = wait.until(EC.presence_of_element_located((By.XPATH, option_xpath)))
            # Grab the target endpoint for fallback/navigation verification
            endpoint = option_li.get_attribute("data-endpoint")
            # Click the inner span to select the option
            option_span = option_li.find_element(By.TAG_NAME, "span")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", option_span)
            driver.execute_script("arguments[0].click();", option_span)

            # Wait for header to reflect selected week
            wait.until(EC.text_to_be_present_in_element(week_picker_span_locator, f"Week {week}"))
            # Wait for table refresh
            if old_table is not None:
                try:
                    wait.until(EC.staleness_of(old_table))
                except TimeoutException:
                    # If staleness didn't trigger, ensure table is present at least
                    wait.until(EC.presence_of_element_located(table_locator))
            else:
                wait.until(EC.presence_of_element_located(table_locator))
        except TimeoutException as exception:
            log.warning("Timeout selecting Week %s via UI: %s", week, exception)
            # Fallback to direct navigation using the endpoint from the option, if available
            try:
                option_li = driver.find_element(By.XPATH, option_xpath)
                endpoint = option_li.get_attribute("data-endpoint")
            except NoSuchElementException:
                endpoint = None

            if endpoint:

                target_url = urljoin(WEB_URL, endpoint)
                log.info("Navigating directly to %s (fallback)", target_url)
                driver.get(target_url)
                # Wait for header and table to be ready
                wait.until(EC.presence_of_element_located(table_locator))
                try:
                    wait.until(
                        EC.text_to_be_present_in_element(week_picker_span_locator, f"Week {week}")
                    )
                except TimeoutException:  # not critical; proceed if table loaded
                    pass
            else:
                # As a last resort, try constructing the URL pattern
                current_year = datetime.now().year
                candidate = f"{WEB_URL}?week={current_year}-reg-{week}&table=true"
                log.info("No endpoint available; navigating to constructed URL %s", candidate)
                driver.get(candidate)
                wait.until(EC.presence_of_element_located(table_locator))
        except WebDriverException as exception:
            log.warning(
                "Unexpected error during week selection; proceeding if tables present: %s",
                exception,
            )
            wait.until(EC.presence_of_element_located(table_locator))

    @staticmethod
    def _find_consensus_index(tbody) -> int:
        """Return the 1-based index among header <th> elements for the Consensus column.

        Note: This returns the index suitable for selecting the corresponding team row <td>
        because the team row has an extra leading cell for the team, making the 0-based
        index in the list of <td> equal to this 1-based header index.
        """
        header_tr = tbody.find("tr")
        if not header_tr:
            raise ValueError("Missing header row in odds table.")
        table_headers = header_tr.find_all("th", recursive=False)
        for idx, table_header in enumerate(table_headers, start=1):
            # Prefer the book image alt, fallback to text
            img = table_header.find("img")
            alt = img.get("alt", "").strip().lower() if img else ""
            label_text = table_header.get_text(strip=True).lower()
            if "consensus" in alt or "consensus" in label_text:
                return idx
        # If not found, assume the last non-empty header is consensus
        for idx in range(len(table_headers), 0, -1):
            if table_headers[idx - 1].get_text(strip=True):
                return idx
        raise ValueError("Consensus column not found in header.")

    @staticmethod
    def _first_td_text(table_row) -> str:
        table_data = table_row.find("td")
        return table_data.get_text(separator=" ", strip=True) if table_data else ""

    @staticmethod
    def _parse_team_name(table_row) -> str:
        """Extract and normalize the team name from a team row.

        Maps nickname (e.g., 'Dolphins') to full name using TEAM_NICKNAME_TO_FULL.
        """
        table_data = table_row.find("td")  # first td is team cell
        text = table_data.get_text(separator=" ", strip=True) if table_data else ""
        # Remove any leading rotation number (three digits)
        text = re.sub(r"^\s*\d{3}\s+", "", text)
        # Take the last token as the nickname (handles 'San Francisco 49ers' -> '49ers')
        # Better approach: try exact nickname lookup by scanning known keys within text
        name = text
        # Try direct match first
        if name in TEAM_NICKNAME_TO_FULL:
            return TEAM_NICKNAME_TO_FULL[name]
        # Try to find any known nickname token within the string
        for nick, full in TEAM_NICKNAME_TO_FULL.items():
            if re.search(rf"\b{re.escape(nick)}\b", name):
                return full
        # Fallback to original text
        return name

    @staticmethod
    def _clean_value_text(raw: str) -> str:
        return raw.replace("\u2212", "-").replace("−", "-").strip()

    def _parse_consensus_value(
        self, team_table_row, consensus_header_index: int, market: str
    ) -> str:
        """Parse the consensus value from a team row for a given market.

        Returns string values per spec:
        - spread: like '+10' or '-3.5' (no price); 'PK' -> '0.0'; blank -> ''
        - total: floating string with one decimal like '47.5'; blank -> ''
        - moneyline: like '+380' or '-165'; blank -> ''
        """
        table_data_cells = team_table_row.find_all("td", recursive=False)
        if not table_data_cells:
            return ""
        # consensus td index equals the 1-based header index
        idx = consensus_header_index
        if idx >= len(table_data_cells):
            # Some weeks add an extra trailing blank cell; try the previous cell
            idx = min(len(table_data_cells) - 1, max(1, idx))

        cell = table_data_cells[idx]
        data_value_element = cell.find("span", class_="data-value")
        raw = (
            data_value_element.get_text(strip=True)
            if data_value_element
            else cell.get_text(strip=True)
        )
        raw = self._clean_value_text(raw)
        norm = raw.strip().lower().replace("’", "'")
        is_missing = (not norm) or norm in {"n/a", "na"}
        is_pick = any(token in norm for token in ["pk", "pick", "pick'em", "pickem"])
        is_even = "even" in norm

        if market == "spread":
            if is_missing or is_pick:
                return f"{float(DEFAULT_SPREAD):.1f}"
            # Expect forms like '+10', '-3.5'
            match_result = re.search(r"^[+\-]?\d+(?:\.\d+)?", raw)
            return match_result.group(0) if match_result else f"{float(DEFAULT_SPREAD):.1f}"
        if market == "moneyline":
            if is_missing or is_even or is_pick:
                return str(int(DEFAULT_MONEYLINE))
            # Forms like '+380', '-165'
            match_result = re.search(r"^[+\-]?\d+", raw)
            return match_result.group(0) if match_result else str(int(DEFAULT_MONEYLINE))
        if market == "total":
            if is_missing:
                return f"{float(DEFAULT_TOTAL):.1f}"
            # Forms like 'o47.5' or 'u47.5' -> extract the number only
            match_result = re.search(r"\d+(?:\.\d+)?", raw)
            return (
                f"{float(match_result.group(0)):.1f}"
                if match_result
                else f"{float(DEFAULT_TOTAL):.1f}"
            )
        return raw

    def _to_mountain_time(self, time_cell_text: str) -> str:
        """Normalize the site's already-local time to 'H:MM AM/PM [NETWORK]'."""
        text = " ".join(time_cell_text.split())
        # Extract date, time, am/pm, and optional network
        time_match = re.search(
            (
                r"(?P<month>\d{1,2})\/"
                r"(?P<day>\d{1,2})\s+"
                r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*"
                r"(?P<ampm>[AP]M)\s*"
            ),
            text,
        )
        if not time_match:
            # Fallback: return original text if parsing fails
            return text

        tmp = datetime(2000, 1, 1, int(time_match.group("hour")), int(time_match.group("minute")))
        formatted_time = tmp.strftime("%I:%M %p").lstrip("0")
        return f"{formatted_time}".strip()

    # -----------------------------
    # Output coercion helpers
    # -----------------------------
    @staticmethod
    def _to_float_or_blank(value: Optional[str]):
        if value is None:
            return ""
        stripped_value = str(value).strip()
        if not stripped_value:
            return ""
        stripped_value = stripped_value.replace("+", "")
        try:
            return float(stripped_value)
        except ValueError:
            return ""

    @staticmethod
    def _to_int_or_blank(value: Optional[str]):
        if value is None:
            return ""
        stripped_value = str(value).strip()
        if not stripped_value:
            return ""
        stripped_value = stripped_value.replace("+", "")
        try:
            return int(stripped_value)
        except ValueError:
            # sometimes moneyline may be empty or malformed
            return ""

    @staticmethod
    def _to_float1_or_blank(value: Optional[str]):
        if value is None:
            return ""
        stripped_value = str(value).strip()
        if not stripped_value:
            return ""
        stripped_value = stripped_value.replace("+", "")
        try:
            return float(f"{float(stripped_value):.1f}")
        except ValueError:
            return ""
        stripped_value = str(value).strip()
        if not stripped_value:
            return ""
        stripped_value = stripped_value.replace("+", "")
        try:
            return float(f"{float(stripped_value):.1f}")
        except ValueError:
            return ""
