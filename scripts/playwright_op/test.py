import re
from playwright.sync_api import Playwright, sync_playwright
import os


def run(playwright: Playwright) -> None:
    print("启动浏览器...")
    browser = playwright.firefox.launch(headless=False)  # 去掉slow_mo以提升速度
    
    # 加载cookies
    cookies_path = os.path.join(os.path.dirname(__file__), "cookies.json")
    if os.path.exists(cookies_path):
        context = browser.new_context(storage_state=cookies_path)
    else:
        context = browser.new_context()
    
    page = context.new_page()
    
    # 打开页面
    print("打开页面...")
    page.goto("https://satellite.nsmc.org.cn/DataPortal/cn/data/dataset.html?dataTypeCode=L1&satelliteCode=FY3F&instrumentTypeCode=HIRAS")
    page.wait_for_load_state("networkidle")
    
    # 点击检索
    print("点击检索...")
    page.get_by_title("检索").click()
    page.wait_for_timeout(500)
    
    # 点击产品选择
    page.locator("div").filter(has_text="产品选择").nth(1).click()
    page.wait_for_timeout(300)
    
    # 设置日期范围
    print("设置日期范围...")
    page.get_by_role("textbox", name="开始日期：").dblclick()
    page.get_by_role("textbox", name="开始日期：").fill("2024/05/01")
    page.get_by_role("textbox", name="结束日期：").dblclick()
    page.get_by_role("textbox", name="结束日期：").fill("2024/08/01")
    page.wait_for_timeout(300)

    # 点击查看文件列表
    print("点击查看文件列表...")
    page.get_by_role("button", name="查看文件列表").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # 设置每页显示100条
    page.locator("#perPageSelect").select_option("100")
    page.wait_for_timeout(1000)
    
    # 关闭可能弹出的面板
    # try:
    #     page.get_by_role("button", name="关闭").click(timeout=2000)
    #     page.wait_for_timeout(500)
    # except:
    #     pass

    # 等待表格加载
    print("等待表格加载...")
    page.wait_for_selector("table tbody tr", timeout=10000)
    page.wait_for_timeout(500)  # 减少等待时间
    
    # 获取总页数
    total_pages = 1
    try:
        page_info = page.locator("text=/当前共有.*页/").first.inner_text(timeout=3000)
        match = re.search(r'(\d+)页', page_info)
        if match:
            total_pages = int(match.group(1))
            print(f"总页数: {total_pages}")
    except:
        print("无法获取总页数，只处理当前页")
    
    # 收集符合条件的数据
    matched_data = []
    total_checked = 0
    
    # 遍历所有页面
    current_page = 1
    while current_page <= total_pages:
        print(f"\n处理第 {current_page}/{total_pages} 页...")
        
        # 获取当前页的行数据
        rows = page.locator("table tbody tr").all()
        print(f"找到 {len(rows)} 行数据")
        
        # 批量获取所有行的时间数据（使用JS批量处理，提升速度）
        print("正在分析数据...")
        row_data_list = page.evaluate("""
            () => {
                const rows = Array.from(document.querySelectorAll('table tbody tr'));
                const result = [];
                rows.forEach((row, index) => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length === 0) return;
                    
                    // 查找时间列
                    let timeText = null;
                    let filename = '';
                    for (let cell of cells) {
                        const text = cell.textContent.trim();
                        if (/\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}/.test(text)) {
                            timeText = text;
                        }
                        if (filename === '' && cells.length > 1 && cell !== cells[0]) {
                            filename = text.substring(0, 50);
                        }
                    }
                    
                    if (timeText) {
                        const match = timeText.match(/(\\d{4}-\\d{2}-\\d{2}) (\\d{2}):(\\d{2}):(\\d{2})/);
                        if (match) {
                            const minute = match[3];
                            if (minute === '00') {
                                result.push({
                                    index: index + 1,
                                    time: match[1] + ' ' + match[2] + ':' + match[3] + ':' + match[4] + ' (UTC)',
                                    filename: filename
                                });
                            }
                        }
                    }
                });
                return result;
            }
        """)
        
        page_checked = 0
        
        # 批量勾选符合条件的复选框
        if row_data_list:
            print(f"找到 {len(row_data_list)} 条符合条件的数据，开始批量勾选...")
            
            # 使用JS批量勾选所有复选框
            checked_count = page.evaluate("""
                (indices) => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    let count = 0;
                    indices.forEach(idx => {
                        const row = rows[idx - 1];
                        if (row) {
                            const checkbox = row.querySelector('input[type="checkbox"]');
                            if (checkbox && !checkbox.checked) {
                                checkbox.checked = true;
                                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                count++;
                            }
                        }
                    });
                    return count;
                }
            """, [item['index'] for item in row_data_list])
            
            page_checked = checked_count
            total_checked += checked_count
            
            # 打印符合条件的数据
            for item in row_data_list:
                matched_data.append({
                    'time': item['time'],
                    'row_index': item['index'],
                    'page': current_page,
                    'filename': item.get('filename', 'N/A')
                })
                print(f"  ✓ 第{item['index']}行 - {item['time']} → 已勾选")
        else:
            print("  未找到符合条件的数据")
        
        print(f"本页勾选: {page_checked} 个")
        
        # 翻到下一页
        # if current_page < total_pages:
        #     try:
        #         next_button = page.locator("text=下一页").first
        #         if next_button.is_visible(timeout=2000):
        #             print(f"\n翻到第 {current_page + 1} 页...")
        #             next_button.click()
        #             page.wait_for_load_state("networkidle")
        #             page.wait_for_timeout(2000)
        #             current_page += 1
        #         else:
        #             break
        #     except:
        #         break
        # else:
        #     break
    
    # 打印所有符合条件的数据
    print("\n" + "="*60)
    print(f"符合条件的数据（整点：分钟为00）共 {len(matched_data)} 条:")
    print("="*60)
    for idx, data in enumerate(matched_data, 1):
        filename = data.get('filename', 'N/A')
        print(f"{idx}. {data['time']} | 文件名: {filename} | 第{data['page']}页第{data['row_index']}行")
    
    print("\n" + "="*60)
    print(f"处理完成！共勾选 {total_checked} 个复选框")
    print("="*60)
    
    # 保持浏览器打开
    print("\n浏览器保持打开状态，手动关闭即可退出...")
    try:
        while True:
            page.wait_for_timeout(10000)
    except KeyboardInterrupt:
        context.close()
        browser.close()


with sync_playwright() as playwright:
    run(playwright)
