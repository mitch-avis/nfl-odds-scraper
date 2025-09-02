# NFL Odds Scraper

## Overview
NFL Odds Scraper is a Python application designed to scrape NFL betting odds from a specified website. It features a user-friendly GUI built with PyQt6 and utilizes Selenium for web scraping. The application is capable of scraping odds for specified weeks and saving the data in Excel format.

## Features
- Scrapes NFL betting odds for specified weeks.
- User-friendly graphical interface.
- Data is saved in Excel format.
- Logging capabilities for tracking events and errors.

## Requirements
To run this project, you need to have Python installed along with the required packages. You can install the necessary packages using the following command:

```bash
pip install -r requirements.txt
```

## Configuration
The application configuration is stored in the `config.ini` file. You can modify the following settings:

- `WebUrl`: The URL of the website to scrape.
- `Timeout`: The maximum time to wait for a page to load.
- `OutputPath`: The directory where the scraped data will be saved.

## Usage
1. Run the application by executing the `main.py` file:
   ```bash
   python src/main.py
   ```
2. Enter the start and end weeks for which you want to scrape odds.
3. Click the "Start" button to begin scraping. You can stop the process at any time by clicking the "Stop" button.
4. The scraped data will be saved in the specified output path in Excel format.

## Packaging
To package the application as a standalone Windows executable, you can use the `build.py` script. This script utilizes tools like PyInstaller or cx_Freeze. Run the following command:

```bash
python build.py
```

## Logging
The application includes logging functionality to help track events and errors. Logs can be found in the console output or can be configured to be saved to a file.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.