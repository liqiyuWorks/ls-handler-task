import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(storage_state="cookies.json")
    page = context.new_page()
    page.goto("https://satellite.nsmc.org.cn/DataPortal/cn/data/dataset.html?dataTypeCode=L1&satelliteCode=FY3F&instrumentTypeCode=HIRAS")
    page.get_by_title("检索").click()
    page.locator("div").filter(has_text="产品选择 每页10条每页20条 搜索 产品名称 全部 FY").nth(1).click()
    
    page.get_by_role("textbox", name="开始日期：").dblclick()
    page.get_by_role("textbox", name="开始日期：").fill("2024/05/01")
    page.get_by_role("textbox", name="结束日期：").dblclick()
    page.get_by_role("textbox", name="结束日期：").fill("2024/08/01")

    page.get_by_role("button", name="查看文件列表").click()
    page.locator("#perPageSelect").select_option("100")

    page.get_by_role("button", name="关闭").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
