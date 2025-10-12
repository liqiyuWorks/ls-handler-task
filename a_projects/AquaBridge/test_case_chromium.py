from playwright.sync_api import Playwright, sync_playwright, TimeoutError
import json
from datetime import datetime
import sys
import time
import platform


def smart_data_extraction(frame_locator):
    """智能数据提取，平衡安全性和完整性"""
    try:
        print("开始智能数据提取...")
        
        # 检查页面状态
        try:
            frame_locator.locator("body").inner_text(timeout=3000)
            print("✓ 页面状态正常")
        except Exception as e:
            print(f"✗ 页面状态异常: {e}")
            return []
        
        # 获取所有表格
        tables = frame_locator.locator("table")
        table_count = tables.count()
        print(f"发现 {table_count} 个表格")
        
        if table_count == 0:
            print("未找到表格，尝试提取页面内容")
            return extract_page_content(frame_locator)
        
        all_data = []
        
        # 处理所有表格，但限制每个表格的大小
        for i in range(table_count):
            try:
                print(f"处理表格 {i+1}...")
                table = tables.nth(i)
                rows = table.locator("tr")
                row_count = rows.count()
                
                print(f"  表格 {i+1} 有 {row_count} 行")
                
                # 智能限制行数：小表格全部提取，大表格限制
                if row_count <= 100:
                    max_rows = row_count
                elif row_count <= 500:
                    max_rows = 100
                else:
                    max_rows = 50
                
                table_data = []
                processed_rows = 0
                
                for j in range(max_rows):
                    try:
                        row = rows.nth(j)
                        cells = row.locator("td, th")
                        cell_count = cells.count()
                        
                        # 智能限制单元格数
                        if cell_count <= 20:
                            max_cells = cell_count
                        else:
                            max_cells = 20
                        
                        row_data = []
                        has_content = False
                        
                        for k in range(max_cells):
                            try:
                                cell_text = cells.nth(k).inner_text(timeout=1000)
                                clean_text = cell_text.strip()[:200]  # 限制长度但不要太短
                                row_data.append(clean_text)
                                if clean_text:
                                    has_content = True
                            except:
                                row_data.append("")
                        
                        # 保存有内容的行
                        if has_content:
                            table_data.append(row_data)
                            processed_rows += 1
                            
                        # 每处理10行检查一次页面状态
                        if j % 10 == 0:
                            try:
                                frame_locator.locator("body").inner_text(timeout=1000)
                            except:
                                print(f"  页面状态异常，停止处理表格 {i+1}")
                                break
                                
                    except Exception as e:
                        print(f"    跳过第{j}行: {e}")
                        continue
                
                if table_data:
                    print(f"  ✓ 表格 {i+1}: {len(table_data)} 行数据")
                    all_data.append({
                        "table_index": i,
                        "total_rows": row_count,
                        "extracted_rows": len(table_data),
                        "rows": table_data
                    })
                else:
                    print(f"  ✗ 表格 {i+1}: 无有效数据")
                    
            except Exception as e:
                print(f"  ✗ 表格 {i+1} 处理失败: {e}")
                continue
        
        return all_data
        
    except Exception as e:
        print(f"智能数据提取失败: {e}")
        return []


def extract_page_content(frame_locator):
    """提取页面文本内容作为备选"""
    try:
        print("提取页面文本内容...")
        body = frame_locator.locator("body")
        text = body.inner_text(timeout=5000)
        
        if text:
            # 按行分割并过滤
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            # 限制行数
            limited_lines = lines[:100]
            
            print(f"提取到 {len(limited_lines)} 行文本")
            return [{
                "table_index": 0,
                "content_type": "text",
                "total_lines": len(lines),
                "extracted_lines": len(limited_lines),
                "rows": [["页面文本"], limited_lines]
            }]
        
        return []
    except Exception as e:
        print(f"页面文本提取失败: {e}")
        return []


def create_stable_chromium_browser(playwright):
    """创建稳定的Chromium浏览器实例"""
    
    # 根据操作系统调整参数
    system = platform.system()
    
    # 基础参数
    base_args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows',
        '--disable-extensions',
        '--disable-plugins',
        '--memory-pressure-off',
        '--disable-ipc-flooding-protection',
        '--disable-hang-monitor',
        '--disable-popup-blocking',
        '--disable-prompt-on-repost',
        '--disable-sync',
        '--disable-translate',
        '--disable-background-networking',
        '--disable-component-extensions-with-background-pages',
        '--disable-component-update',
        '--disable-default-apps',
        '--disable-field-trial-config',
        '--disable-client-side-phishing-detection',
        '--disable-breakpad'
    ]
    
    # macOS特定优化
    if system == "Darwin":
        base_args.extend([
            '--disable-features=TranslateUI',
            '--disable-features=BlinkGenPropertyTrees',
            '--disable-features=EnableDrDc',
            '--disable-features=VaapiVideoDecoder',
            '--disable-features=VaapiVideoEncoder',
            '--max_old_space_size=2048',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-first-run',
            '--password-store=basic',
            '--use-mock-keychain',
            '--no-service-autorun',
            '--disable-search-engine-choice-screen',
            '--enable-use-zoom-for-dsf=false'
        ])
    elif system == "Linux":
        base_args.extend([
            '--disable-features=TranslateUI',
            '--max_old_space_size=3072',
            '--disable-software-rasterizer'
        ])
    else:  # Windows
        base_args.extend([
            '--disable-features=TranslateUI',
            '--max_old_space_size=4096',
            '--disable-software-rasterizer'
        ])
    
    browser = playwright.chromium.launch(
        headless=False,
        args=base_args
    )
    
    # 创建上下文
    context = browser.new_context(
        viewport={'width': 1200, 'height': 800},
        java_script_enabled=True,
        ignore_https_errors=True,
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    return browser, context


def safe_operation(frame, selector, operation="click", text=None, timeout=3000):
    """安全的页面操作"""
    try:
        element = frame.locator(selector).first
        element.wait_for(state="visible", timeout=timeout)
        
        if operation == "click":
            element.click()
        elif operation == "fill" and text:
            element.click()
            element.fill(text)
        
        time.sleep(0.5)  # Chromium需要稍长的等待时间
        return True
    except Exception as e:
        print(f"操作失败 {operation} {selector}: {e}")
        return False


def save_screenshot(page, prefix="error"):
    """保存截图"""
    try:
        screenshot_path = f"{prefix}_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=screenshot_path)
        print(f"截图已保存: {screenshot_path}")
    except:
        pass


def run(playwright: Playwright) -> None:
    browser = None
    context = None
    page = None
    
    try:
        print("初始化Chromium浏览器 (稳定性优化版)...")
        print("注意: Chromium在某些系统上可能不稳定，如果遇到崩溃请使用Firefox版本")
        
        browser, context = create_stable_chromium_browser(playwright)
        page = context.new_page()
        
        # 设置超时
        page.set_default_timeout(15000)  # Chromium需要更长超时
        page.set_default_navigation_timeout(20000)
        
        print("1. 访问网站...")
        page.goto("https://jinzhengny.com/", wait_until="domcontentloaded", timeout=20000)
        
        print("2. 等待页面加载...")
        page.locator("#reportFrame").wait_for(state="visible", timeout=15000)
        
        print("3. 开始登录...")
        report_frame = page.frame_locator("#reportFrame")
        
        # 登录
        username_selectors = [
            "input[placeholder*='Username']",
            "input[placeholder*='用户名']",
            "input[type='text']"
        ]
        
        for selector in username_selectors:
            if safe_operation(report_frame, selector, "fill", "15152627161"):
                break
        
        if not safe_operation(report_frame, "input[type='password']", "fill", "lsls12"):
            print("密码输入失败")
        
        # 登录按钮
        login_selectors = [
            ".bi-h-o > .bi-basic-button",
            "button[type='submit']",
            "button"
        ]
        
        for selector in login_selectors:
            if safe_operation(report_frame, selector):
                break
        
        print("4. 等待登录完成...")
        report_frame.locator(".bi-f-c > .bi-icon-change-button").first.wait_for(state="visible", timeout=12000)
        
        print("5. 导航到目标页面...")
        nav_steps = [
            ".bi-f-c > .bi-icon-change-button > .x-icon",
            "div:nth-child(2) > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
            "div:nth-child(2) > div > div:nth-child(2) > .bi-custom-tree > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
        ]
        
        for selector in nav_steps:
            safe_operation(report_frame, selector)
        
        safe_operation(report_frame, "div:nth-child(3) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon")
        
        print("6. 点击目标菜单项...")
        safe_operation(report_frame, "text='现货应用决策'")
        
        print("7. 等待iframe加载...")
        time.sleep(3)  # Chromium需要更长的等待时间
        
        # 找到目标iframe
        inner_frames = report_frame.locator("iframe")
        frame_count = inner_frames.count()
        print(f"找到 {frame_count} 个iframe")
        
        target_frame = None
        for i in range(frame_count):
            try:
                if inner_frames.nth(i).is_visible(timeout=3000):
                    target_frame = report_frame.frame_locator("iframe").nth(i)
                    print(f"使用iframe {i}")
                    break
            except:
                continue
        
        if not target_frame:
            target_frame = report_frame.frame_locator("iframe").first
        
        print("8. 尝试点击查询按钮...")
        query_selectors = [
            "button:has-text('查询')",
            "button:has-text('Query')",
            "button[type='submit']",
            "input[type='submit']"
        ]
        
        query_clicked = False
        for selector in query_selectors:
            if safe_operation(target_frame, selector):
                query_clicked = True
                break
        
        if query_clicked:
            print("   查询已执行，等待数据加载...")
            time.sleep(5)  # Chromium需要更长的数据加载时间
        
        print("9. 开始智能数据提取...")
        table_data = smart_data_extraction(target_frame)
        
        # 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if table_data:
            json_file = f"extracted_data_{timestamp}.json"
            
            # 计算统计信息
            total_rows = sum(table.get("extracted_rows", len(table.get("rows", []))) for table in table_data)
            total_tables = len(table_data)
            
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": timestamp,
                    "browser_used": "chromium",
                    "extraction_method": "smart_extraction",
                    "statistics": {
                        "total_tables": total_tables,
                        "total_rows": total_rows
                    },
                    "tables": table_data
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ 数据已保存到: {json_file}")
            print(f"✓ 成功提取 {total_tables} 个表格，共 {total_rows} 行数据")
            print(f"✓ 使用浏览器: Chromium (稳定性优化版)")
            
            # 显示数据概览
            for i, table in enumerate(table_data):
                if "content_type" in table:
                    print(f"  - 表格 {i+1}: {table['content_type']} 内容，{table['extracted_lines']} 行")
                else:
                    print(f"  - 表格 {i+1}: {table['extracted_rows']} 行 (共 {table['total_rows']} 行)")
            
        else:
            print("\n✗ 未能提取到数据")
            save_screenshot(page, "no_data")
        
        print("\n✓ 程序执行完成！")
        try:
            input("按回车键关闭浏览器...")
        except EOFError:
            print("2秒后自动关闭...")
            time.sleep(2)
        
    except TimeoutError as e:
        print(f"\n✗ 超时错误: {e}")
        print("如果频繁出现此错误，建议使用Firefox版本: python3 test_case_firefox.py")
        save_screenshot(page, "timeout")
        try:
            input("按回车键关闭浏览器...")
        except EOFError:
            pass
        
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        print("如果遇到崩溃问题，建议使用Firefox版本: python3 test_case_firefox.py")
        save_screenshot(page, "error")
        try:
            input("按回车键关闭浏览器...")
        except EOFError:
            pass
    
    finally:
        try:
            if page:
                page.close()
        except:
            pass
        try:
            if context:
                context.close()
        except:
            pass
        try:
            if browser:
                browser.close()
        except:
            pass


if __name__ == "__main__":
    try:
        with sync_playwright() as playwright:
            run(playwright)
    except KeyboardInterrupt:
        print("\n用户中断程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序启动失败: {e}")
        print("建议安装Chromium: python3 -m playwright install chromium")
        sys.exit(1)
