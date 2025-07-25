#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import traceback
from pkg.public.decorator import decorate
import pymongo
import requests
import datetime
from pkg.public.models import BaseModel
from playwright.sync_api import Playwright, sync_playwright, expect
import time
import os
import re



class SpiderVesselFinderVessels(BaseModel):
    # 常量集中管理
    page_start = int(os.getenv("PAGE_START", 1))
    page_end = int(os.getenv("PAGE_END", 133))
    VESSEL_LIST_URL_BASE = "https://www.vesselfinder.com/vessels?page={page}"
    LINK_SELECTOR = "table tbody tr td:first-child a"
    NEXT_PAGE_ROLE = "link"
    NEXT_PAGE_NAME = "next page"

    def __init__(self):
        self.page = int(os.getenv("PAGE", 1))
        self.VESSEL_LIST_URL_START = self.VESSEL_LIST_URL_BASE.format(page=self.page_start)
        self.VESSEL_LIST_URL_END = self.VESSEL_LIST_URL_BASE.format(page=self.page_end)
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'vessel_finder_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }
        super(SpiderVesselFinderVessels, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        """
        入口方法，负责Playwright上下文管理和异常捕获
        """
        try:
            with sync_playwright() as playwright:
                self._crawl_vessels(playwright)
        except Exception as e:
            print(f"[SpiderVesselFinderVessels][run] error: {e}")

    def _crawl_vessels(self, playwright: Playwright):
        """
        负责爬取船舶数据，返回vessels列表
        """
        data_time = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        print(f"[SpiderVesselFinderVessels][crawl] data_time: {data_time}")
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        vessels = []
        try:
            for page_num in range(self.page_start, self.page_end + 1):
                try:
                    url = self.VESSEL_LIST_URL_BASE.format(page=page_num)
                    print(f"Crawling page: {url}")
                    page.goto(url, timeout=60000)
                    page.wait_for_selector("table tbody tr", timeout=60000)
                    page.wait_for_timeout(10)  # 等待新页面加载
                    rows = page.query_selector_all("table tbody tr")
                    for row in rows:
                        tds = row.query_selector_all("td")
                        # 采集所有可见字段，按实际页面顺序调整字段名
                        a_tag = tds[0].query_selector("a") if len(tds) > 0 else None
                        name = ""
                        vtype = ""
                        imo = ""
                        mmsi = ""
                        href = ""
                        ship_img = ""
                        if a_tag:
                            # 船名
                            name_lines = a_tag.inner_text().split('\n')
                            name = name_lines[0].strip() if len(name_lines) > 0 else ""
                            vtype = name_lines[1].strip() if len(name_lines) > 1 else ""
                            href = a_tag.get_attribute("href") or ""
                            # IMO/MMSI
                            img_tag = a_tag.query_selector("div img")
                            if img_tag:
                                ship_img = img_tag.get_attribute("data-src") or img_tag.get_attribute("src") or ""
                                src = ship_img
                                ship_img = src or ""
                                match = re.search(r'/ship-photo/(\d+)-(\d+)-', src) if src else None
                                if match:
                                    imo = match.group(1)
                                    mmsi = match.group(2)
                            if not imo and href:
                                match = re.search(r'/details/(\d+)', href)
                                if match:
                                    imo = match.group(1)
                        vessel = {
                            "name": name,
                            "type": vtype,
                            "imo": imo,
                            "mmsi": mmsi,
                            "built": tds[1].inner_text().strip() if len(tds) > 1 else "",
                            "gt": tds[2].inner_text().strip() if len(tds) > 2 else "",
                            "dwt": tds[3].inner_text().strip() if len(tds) > 3 else "",
                            "size": tds[4].inner_text().strip() if len(tds) > 4 else "",
                            "ship_img": ship_img,
                            "href": href,
                        }
                        print(vessel)
                        self.save_to_db(vessel)
                except Exception as page_exc:
                    print(f"[SpiderVesselFinderVessels][crawl][page {page_num}] error: {page_exc}")
                    traceback.print_exc()
                    continue

                
                # 尝试点击下一页
                # try:
                #     next_btns = page.get_by_role(self.NEXT_PAGE_ROLE, name=self.NEXT_PAGE_NAME)
                #     if next_btns.count() == 0:
                #         # 尝试用xpath查找下一页
                #         xpath = '/html/body/div[1]/div/main/div[1]/div/nav[1]/div[2]/a'
                #         xpath_btns = page.query_selector_all(f'xpath={xpath}')
                #         if not xpath_btns:
                #             break  # 没有下一页
                #         next_btn = xpath_btns[0]
                #     else:
                #         next_btn = next_btns.nth(0)
                #     if next_btn.is_disabled() if hasattr(next_btn, 'is_disabled') else False:
                #         break
                #     next_btn.click()
                #     page.wait_for_timeout(1000)  # 等待新页面加载
        except Exception:
            traceback.print_exc()
        finally:
            page.close()
            context.close()
            browser.close()
        return vessels

    #可扩展：数据存储方法
    def save_to_db(self, vessel):
        self.mgo.set(None, vessel)
