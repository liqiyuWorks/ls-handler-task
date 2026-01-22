# -*- coding: utf-8 -*-
"""应用配置"""

import os

APP_TITLE = os.getenv("APP_TITLE", "Dynamic XPath Parser API")
APP_DESC = os.getenv(
    "APP_DESC",
    "API to extract data from dynamic webpages using XPath and Playwright.",
)
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Playwright
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
NAVIGATE_TIMEOUT = int(os.getenv("NAVIGATE_TIMEOUT", "30000"))
SELECTOR_TIMEOUT = int(os.getenv("SELECTOR_TIMEOUT", "10000"))
