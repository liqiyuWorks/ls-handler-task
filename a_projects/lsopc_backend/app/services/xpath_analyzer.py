# -*- coding: utf-8 -*-
"""XPath 解析服务：Playwright 抓取 + lxml 解析"""

import logging
from typing import List

from lxml import etree
from playwright.sync_api import sync_playwright

from app.config import (
    NAVIGATE_TIMEOUT,
    PLAYWRIGHT_HEADLESS,
    SELECTOR_TIMEOUT,
)

logger = logging.getLogger(__name__)


class XpathAnalyzer:
    """使用 Playwright 抓取动态页面，并用 XPath 提取数据"""

    def fetch_and_parse(self, url: str, xpath_expression: str) -> List[str]:
        """请求 URL，等待 JS 执行后按 XPath 解析"""
        results: List[str] = []
        with sync_playwright() as p:
            try:
                logger.info("Launching browser...")
                browser = p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
                page = browser.new_page()

                logger.info("Navigating to: %s", url)
                page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATE_TIMEOUT)

                try:
                    logger.info("Waiting for element: %s", xpath_expression)
                    page.wait_for_selector(
                        f"xpath={xpath_expression}",
                        timeout=SELECTOR_TIMEOUT,
                    )
                except Exception as e:
                    logger.warning("Wait for selector failed: %s", e)

                content = page.content()
                browser.close()
                results = self._parse_html(content, xpath_expression)

            except Exception as e:
                logger.error("Browser interaction failed: %s", e)
                if "browser" in locals():
                    browser.close()
                raise

        return results

    def _parse_html(self, content: str, xpath_expression: str) -> List[str]:
        """用 lxml 解析 HTML 并执行 XPath"""
        try:
            parser = etree.HTMLParser(encoding="utf-8")
            tree = etree.HTML(content, parser=parser)
            if tree is None:
                logger.error("Failed to create HTML tree.")
                return []

            raw = tree.xpath(xpath_expression)
            clean: List[str] = []
            for r in raw:
                if isinstance(r, etree._Element):
                    html = etree.tostring(r, encoding="unicode").strip()
                    if html:
                        clean.append(html)
                else:
                    clean.append(str(r).strip())
            return clean

        except Exception as e:
            logger.error("XPath parse error: %s", e)
            return []
