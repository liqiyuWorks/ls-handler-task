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



class SpiderVesselFinderVessels(BaseModel):
    # 常量集中管理
    VESSEL_LIST_URL = "https://www.vesselfinder.com/vessels"  # page=133
    LINK_SELECTOR = "table tbody tr td:first-child a"
    NEXT_PAGE_ROLE = "link"
    NEXT_PAGE_NAME = "next page"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'vessel_finder_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
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
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(self.VESSEL_LIST_URL)
        vessels = []
        try:
            while True:
                page.wait_for_selector(self.LINK_SELECTOR)
                links = page.query_selector_all(self.LINK_SELECTOR)
                for a in links:
                    href = a.get_attribute("href")
                    if not href:
                        continue
                    div3 = a.query_selector("div:nth-child(3)")
                    if div3:
                        slna_elem = div3.query_selector(".slna")
                        slty_elem = div3.query_selector(".slty")
                        name = slna_elem.inner_text().strip() if slna_elem else ""
                        vtype = slty_elem.inner_text().strip() if slty_elem else ""
                    else:
                        name = ""
                        vtype = ""

                    imo = href.split("/")[-1]
                    vessel = {"imo": imo, "href": href,
                              "name": name, "type": vtype}
                    print(vessel)
                    self.save_to_db(vessel)
                # 尝试点击下一页
                try:
                    next_btns = page.get_by_role(self.NEXT_PAGE_ROLE, name=self.NEXT_PAGE_NAME)
                    if next_btns.count() == 0:
                        # 尝试用xpath查找下一页
                        xpath = '/html/body/div[1]/div/main/div[1]/div/nav[1]/div[2]/a'
                        xpath_btns = page.query_selector_all(f'xpath={xpath}')
                        if not xpath_btns:
                            break  # 没有下一页
                        next_btn = xpath_btns[0]
                    else:
                        next_btn = next_btns.nth(0)
                    if next_btn.is_disabled() if hasattr(next_btn, 'is_disabled') else False:
                        break
                    next_btn.click()
                    page.wait_for_timeout(1000)  # 等待新页面加载
                except Exception:
                    traceback.print_exc()
                    break
        finally:
            page.close()
            context.close()
            browser.close()
        return vessels

    #可扩展：数据存储方法
    def save_to_db(self, vessel):
        self.mgo.set(None, vessel)
