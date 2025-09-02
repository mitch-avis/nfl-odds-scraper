"""Build script for creating a standalone Windows executable using PyInstaller."""

import os
import subprocess


def build_exe():
    """Builds the executable."""
    # Ensure we're in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Use the venv's PyInstaller executable directly
    pyinstaller_exe = os.path.join(project_root, "venv", "Scripts", "pyinstaller.exe")

    # PyInstaller command
    cmd = [
        pyinstaller_exe,  # Use the executable directly
        "--onefile",  # Single .exe file
        "--windowed",  # No console window
        "--name",
        "NFL_Odds_Scraper",
        "--add-data",
        "config.ini;.",  # Include config
        "--hidden-import",
        "selenium",  # Ensure Selenium is bundled
        "--hidden-import",
        "PyQt6",
        "--hidden-import",
        "selenium.webdriver.chrome.service",  # ChromeDriver service
        "--hidden-import",
        "selenium.webdriver.chrome.options",  # Chrome options
        "--hidden-import",
        "coloredlogs",  # Logging
        "src/main.py",
    ]

    subprocess.run(cmd, check=True)
    print("Executable built successfully in 'dist/' folder.")


if __name__ == "__main__":
    build_exe()
