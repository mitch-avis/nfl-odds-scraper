"""Shared constants for the NFL Odds Scraper application.

Includes robust discovery of ``config.ini`` both in development and when frozen
with PyInstaller (onefile). Provides resolved paths for outputs and logging.
"""

import configparser
import os
import sys
from pathlib import Path


def _find_config_path() -> Path:
    """Return the path to config.ini in dev or frozen builds.

    Search order:
    - Current working directory
    - If frozen: sys._MEIPASS (PyInstaller temp) / executable directory
    - Project root (parent of src) in dev
    """
    candidates = [Path("config.ini").resolve()]
    if getattr(sys, "frozen", False):  # PyInstaller onefile/onedir
        meipass = Path(getattr(sys, "_MEIPASS", "")) if hasattr(sys, "_MEIPASS") else None
        exe_dir = Path(sys.executable).resolve().parent
        if meipass:
            candidates.append(meipass / "config.ini")
        candidates.append(exe_dir / "config.ini")
    else:
        # project root two levels up from this file (src/constants.py -> project)
        candidates.append(Path(__file__).resolve().parents[1] / "config.ini")
    for p in candidates:
        if p.is_file():
            return p
    # fallback to first candidate (CWD)
    return candidates[0]


# Load config
CONFIG_PATH = _find_config_path()
config = configparser.ConfigParser()
config.read(CONFIG_PATH.as_posix())

# Constants
WEB_URL = config["DEFAULT"]["WebUrl"]
TIMEOUT = int(config["DEFAULT"]["Timeout"])
_output_raw = config["DEFAULT"]["OutputPath"]
OUTPUT_PATH = (
    Path(_output_raw).resolve()
    if os.path.isabs(_output_raw)
    else (CONFIG_PATH.parent / _output_raw).resolve()
)
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

# Optional log path (file). If relative, resolve relative to the config location.
_log_path_raw = config["DEFAULT"].get("LogPath", "").strip()
LOG_PATH = None
if _log_path_raw:
    LOG_PATH = (
        Path(_log_path_raw).resolve()
        if os.path.isabs(_log_path_raw)
        else (CONFIG_PATH.parent / _log_path_raw).resolve()
    )
