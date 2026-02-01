# -*- coding: utf-8 -*-
"""XPath 解析服务：Playwright 抓取 + lxml 解析"""

import logging
from typing import List

from lxml import etree
from playwright.sync_api import sync_playwright

from app.config import settings

logger = logging.getLogger(__name__)


class XpathAnalyzer:
    """使用 Playwright 抓取动态页面，并用 XPath 提取数据"""

    def fetch_and_parse(self, url: str, xpath_expression: str) -> List[str]:
        """
        请求 URL，等待 JS 执行后按 XPath 解析。

        :param url: 目标网页 URL
        :param xpath_expression: XPath 表达式
        :return: 提取到的字符串列表
        """
        results: List[str] = []
        with sync_playwright() as p:
            try:
                logger.info("Launching browser (headless=%s)...", settings.PLAYWRIGHT_HEADLESS)
                browser = p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
                page = browser.new_page()

                logger.info("Navigating to: %s", url)
                page.goto(url, wait_until="domcontentloaded", timeout=settings.NAVIGATE_TIMEOUT)

                try:
                    logger.info("Waiting for element: %s", xpath_expression)
                    page.wait_for_selector(
                        f"xpath={xpath_expression}",
                        timeout=settings.SELECTOR_TIMEOUT,
                    )
                except Exception as e:
                    logger.warning("Wait for selector timed out or failed: %s", e)

                content = page.content()
                browser.close()
                results = self._parse_html(content, xpath_expression)

            except Exception as e:
                logger.error("Browser interaction failed for URL %s: %s", url, e)
                # Ensure browser is closed if it exists and an error occurs
                if "browser" in locals():
                    browser.close()
                raise

        return results

    def _parse_html(self, content: str, xpath_expression: str) -> List[str]:
        """
        使用 lxml 解析 HTML 并执行 XPath。

        :param content: HTML 字符串
        :param xpath_expression: XPath 表达式
        :return: 提取到的结果列表
        """
        try:
            parser = etree.HTMLParser(encoding="utf-8")
            tree = etree.HTML(content, parser=parser)
            if tree is None:
                logger.error("Failed to create HTML tree from content.")
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
            
            logger.info("XPath extraction completed. Found %d items.", len(clean))
            return clean

        except Exception as e:
            logger.error("XPath parse error for expression '%s': %s", xpath_expression, e)
            return []
