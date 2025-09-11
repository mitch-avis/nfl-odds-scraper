"""Shared constants for the NFL Odds Scraper application."""

import configparser
from pathlib import Path

# Load config
config = configparser.ConfigParser()
config.read("config.ini")

# Constants
WEB_URL = config["DEFAULT"]["WebUrl"]
TIMEOUT = int(config["DEFAULT"]["Timeout"])
OUTPUT_PATH = Path(config["DEFAULT"]["OutputPath"])
WINDOW_WIDTH = 300
WINDOW_HEIGHT = 200

# Team mapping for data processing
TEAM_MAPPING = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

# Optional nickname-to-full-name mapping for sites that show only short names
# e.g., "Dolphins" -> "Miami Dolphins". Used by the VegasInsider scraper.
TEAM_NICKNAME_TO_FULL = {
    "Cardinals": "Arizona Cardinals",
    "Falcons": "Atlanta Falcons",
    "Ravens": "Baltimore Ravens",
    "Bills": "Buffalo Bills",
    "Panthers": "Carolina Panthers",
    "Bears": "Chicago Bears",
    "Bengals": "Cincinnati Bengals",
    "Browns": "Cleveland Browns",
    "Cowboys": "Dallas Cowboys",
    "Broncos": "Denver Broncos",
    "Lions": "Detroit Lions",
    "Packers": "Green Bay Packers",
    "Texans": "Houston Texans",
    "Colts": "Indianapolis Colts",
    "Jaguars": "Jacksonville Jaguars",
    "Chiefs": "Kansas City Chiefs",
    "Chargers": "Los Angeles Chargers",
    "Rams": "Los Angeles Rams",
    "Raiders": "Las Vegas Raiders",
    "Dolphins": "Miami Dolphins",
    "Vikings": "Minnesota Vikings",
    "Patriots": "New England Patriots",
    "Saints": "New Orleans Saints",
    "Giants": "New York Giants",
    "Jets": "New York Jets",
    "Eagles": "Philadelphia Eagles",
    "Steelers": "Pittsburgh Steelers",
    "Seahawks": "Seattle Seahawks",
    "49ers": "San Francisco 49ers",
    "Buccaneers": "Tampa Bay Buccaneers",
    "Titans": "Tennessee Titans",
    "Commanders": "Washington Commanders",
}

DEFAULT_SPREAD = 0.0
DEFAULT_TOTAL = 44.2
DEFAULT_MONEYLINE = -110
