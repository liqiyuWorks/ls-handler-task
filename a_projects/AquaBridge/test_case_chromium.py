"""
优化版 Chromium 自动化测试脚本
- 更简洁的代码结构
- 更高效的执行性能
- 更稳定的错误处理
"""
from playwright.sync_api import Playwright, sync_playwright, TimeoutError
import json
from datetime import datetime
import sys
import time


def extract_table_data(frame_locator, max_rows=100, max_cells=20):
    """提取表格数据"""
    try:
        tables = frame_locator.locator("table")
        table_count = tables.count()
        
        if table_count == 0:
            print("未找到表格")
            return []
        
        print(f"发现 {table_count} 个表格")
        all_data = []
        
        for i in range(table_count):
            try:
                rows = tables.nth(i).locator("tr")
                row_count = rows.count()
                limit = min(row_count, max_rows)
                
                table_data = []
                for j in range(limit):
                    try:
                        cells = rows.nth(j).locator("td, th")
                        cell_count = min(cells.count(), max_cells)
                        
                        row_data = []
                        for k in range(cell_count):
                            try:
                                text = cells.nth(k).inner_text(timeout=1000).strip()[:200]
                                row_data.append(text)
                            except:
                                row_data.append("")
                        
                        if any(row_data):  # 只保存有内容的行
                            table_data.append(row_data)
                    except:
                        continue
                
                if table_data:
                    all_data.append({
                        "table_index": i,
                        "total_rows": row_count,
                        "extracted_rows": len(table_data),
                        "rows": table_data
                    })
                    print(f"  表格 {i+1}: {len(table_data)}/{row_count} 行")
            except Exception as e:
                print(f"  表格 {i+1} 失败: {e}")
                continue
        
        return all_data
    except Exception as e:
        print(f"数据提取失败: {e}")
        return []


def create_browser(playwright, headless=False):
    """创建浏览器实例"""
    # 精简且有效的启动参数
    args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor,TranslateUI',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-extensions',
        '--disable-sync',
        '--disable-translate',
        '--memory-pressure-off'
    ]
    
    browser = playwright.chromium.launch(headless=headless, args=args)
    context = browser.new_context(
        viewport={'width': 1280, 'height': 800},
        ignore_https_errors=True
    )
    
    return browser, context


def try_click(frame, selectors, operation="click", text=None, timeout=3000):
    """尝试多个选择器直到成功"""
    if isinstance(selectors, str):
        selectors = [selectors]
    
    for selector in selectors:
        try:
            element = frame.locator(selector).first
            element.wait_for(state="visible", timeout=timeout)
            
            if operation == "fill" and text:
                element.fill(text)
            else:
                element.click()
            
            time.sleep(0.3)
            return True
        except:
            continue
    return False


def save_data_as_txt(data, timestamp, browser_name="chromium"):
    """直接保存数据为 TXT 文件"""
    txt_filename = f"extracted_data_{timestamp}.txt"
    
    with open(txt_filename, "w", encoding="utf-8") as f:
        # 写入每个表格的内容
        for table in data:
            rows = table.get("rows", [])
            for row in rows:
                # 过滤空单元格并连接
                # cells = [str(cell).strip() for cell in row if str(cell).strip()]
                # if cells:
                f.write("\t".join(row) + "\n")
            f.write("\n")  # 表格之间空行
    
    return txt_filename


def save_data(data, browser_name="chromium"):
    """保存提取的数据（JSON 和 TXT 格式）"""
    if not data:
        print("✗ 无数据可保存")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_rows = sum(t.get("extracted_rows", 0) for t in data)
    
    # 保存 JSON 文件
    json_filename = f"extracted_data_{timestamp}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "browser": browser_name,
            "statistics": {
                "total_tables": len(data),
                "total_rows": total_rows
            },
            "tables": data
        }, f, ensure_ascii=False, indent=2)
    
    # 保存 TXT 文件
    txt_filename = save_data_as_txt(data, timestamp, browser_name)
    
    print(f"\n✓ 数据已保存:")
    print(f"  - JSON: {json_filename}")
    print(f"  - TXT:  {txt_filename}")
    print(f"✓ {len(data)} 个表格, {total_rows} 行数据")
    return True


def run(playwright: Playwright) -> None:
    """主执行函数"""
    browser = context = page = None
    
    try:
        print("初始化浏览器...")
        browser, context = create_browser(playwright, headless=True)
        page = context.new_page()
        page.set_default_timeout(12000)
        page.set_default_navigation_timeout(15000)
        
        # 1. 访问网站
        print("1. 访问网站...")
        page.goto("https://jinzhengny.com/", wait_until="domcontentloaded")
        page.locator("#reportFrame").wait_for(state="visible")
        
        report_frame = page.frame_locator("#reportFrame")
        
        # 2. 登录
        print("2. 登录...")
        try_click(report_frame, [
            "input[placeholder*='Username']",
            "input[placeholder*='用户名']",
            "input[type='text']"
        ], "fill", "15152627161")
        
        try_click(report_frame, "input[type='password']", "fill", "lsls12")
        
        try_click(report_frame, [
            ".bi-h-o > .bi-basic-button",
            "button[type='submit']",
            "button"
        ])
        
        # 3. 等待登录完成
        print("3. 等待登录...")
        report_frame.locator(".bi-f-c > .bi-icon-change-button").first.wait_for(
            state="visible", timeout=10000
        )
        
        # 4. 导航
        print("4. 导航到目标页面...")
        nav_selectors = [
            ".bi-f-c > .bi-icon-change-button > .x-icon",
            "div:nth-child(2) > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
            "div:nth-child(2) > div > div:nth-child(2) > .bi-custom-tree > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
            "div:nth-child(3) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon"
        ]
        
        for selector in nav_selectors:
            try_click(report_frame, selector)
        
        try_click(report_frame, "text='现货应用决策'")
        
        # 5. 找到目标 iframe
        print("5. 等待数据加载...")
        time.sleep(2)
        
        inner_frames = report_frame.locator("iframe")
        target_frame = None
        
        for i in range(inner_frames.count()):
            try:
                if inner_frames.nth(i).is_visible(timeout=2000):
                    target_frame = report_frame.frame_locator("iframe").nth(i)
                    break
            except:
                continue
        
        if not target_frame:
            target_frame = report_frame.frame_locator("iframe").first
        
        # 6. 查询数据
        if try_click(target_frame, [
            "button:has-text('查询')",
            "button[type='submit']"
        ]):
            print("6. 查询执行，等待响应...")
            time.sleep(3)
        
        # 7. 提取数据
        print("7. 提取数据...")
        table_data = extract_table_data(target_frame)
        
        # 8. 保存数据
        save_data(table_data)
        
        print("\n✓ 执行完成")
        
        # 等待用户
        try:
            input("\n按回车键关闭...")
        except EOFError:
            time.sleep(2)
    
    except TimeoutError as e:
        print(f"\n✗ 超时: {e}")
        if page:
            try:
                page.screenshot(path=f"timeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            except:
                pass
    
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        if page:
            try:
                page.screenshot(path=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            except:
                pass
    
    finally:
        # 清理资源
        for obj in [page, context, browser]:
            if obj:
                try:
                    obj.close()
                except:
                    pass


if __name__ == "__main__":
    try:
        with sync_playwright() as playwright:
            run(playwright)
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n启动失败: {e}")
        sys.exit(1)
