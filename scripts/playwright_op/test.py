import re
from playwright.sync_api import Playwright, sync_playwright
import os


def run(playwright: Playwright) -> None:
    print("启动浏览器...")
    browser = playwright.firefox.launch(headless=False)
    
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
    page.wait_for_timeout(1000)
    
    # 点击产品选择
    print("点击产品选择...")
    page.locator("div").filter(has_text="产品选择").nth(1).click()
    page.wait_for_timeout(500)
    
    # 设置日期范围
    print("设置日期范围...")
    page.get_by_role("textbox", name="开始日期：").dblclick()
    page.get_by_role("textbox", name="开始日期：").fill("2024/05/01")
    page.get_by_role("textbox", name="结束日期：").dblclick()
    page.get_by_role("textbox", name="结束日期：").fill("2024/08/01")
    page.wait_for_timeout(500)

    # 点击查看文件列表
    print("点击查看文件列表...")
    view_button = page.get_by_role("button", name="查看文件列表")
    view_button.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    
    # 设置每页显示100条
    print("设置每页显示100条...")
    page.locator("#perPageSelect").select_option("100")
    page.wait_for_timeout(1500)  # 等待分页更新
    
    

    # 等待表格加载
    print("等待表格加载...")
    page.wait_for_selector("table tbody tr", timeout=10000)
    page.wait_for_timeout(1000)
    
    # 获取总页数
    total_pages = 1
    try:
        page_info = page.locator("text=/当前共有.*页/").first.inner_text(timeout=5000)
        print(f"分页信息原始文本: {repr(page_info)}")  # 使用repr查看原始字符
        
        # 尝试多种正则表达式匹配页数
        match = None
        
        # 方式1: 标准匹配 "当前共有 262 页"
        match = re.search(r'(\d+)\s*页', page_info)
        if match:
            print(f"方式1匹配成功: {match.group(1)}")
        
        # 方式2: 匹配 "共有 262 页"
        if not match:
            match = re.search(r'共有\s*(\d+)\s*页', page_info)
            if match:
                print(f"方式2匹配成功: {match.group(1)}")
        
        # 方式3: 更宽泛的匹配，匹配数字后跟页
        if not match:
            match = re.search(r'(\d+).*?页', page_info)
            if match:
                print(f"方式3匹配成功: {match.group(1)}")
        
        # 方式4: 直接查找所有数字，取第一个较大的数字（通常是页数）
        if not match:
            numbers = re.findall(r'\d+', page_info)
            if numbers:
                # 页数通常是较大的数字，取第一个
                total_pages = int(numbers[0])
                print(f"方式4匹配成功（取第一个数字）: {total_pages}")
            else:
                print(f"✗ 无法从分页信息中提取页数: {page_info}")
        else:
            total_pages = int(match.group(1))
            print(f"✓ 成功提取总页数: {total_pages}")
            
        if total_pages > 1:
            print(f"将处理所有 {total_pages} 页数据")
            
    except Exception as e:
        print(f"✗ 无法获取总页数: {e}")
        import traceback
        traceback.print_exc()
        print("将只处理当前页")
    
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
        
        page_checked = 0
        
        for i, row in enumerate(rows):
            try:
                cells = row.locator("td").all()
                if len(cells) == 0:
                    continue
                
                # 查找时间列
                time_text = None
                for cell in cells:
                    cell_text = cell.inner_text().strip()
                    if re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', cell_text):
                        time_text = cell_text
                        break
                
                if not time_text:
                    continue
                
                # 提取时间并检查是否为整点（分钟为00）
                time_match = re.search(r'(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})', time_text)
                if time_match:
                    date_str = time_match.group(1)
                    hour = time_match.group(2)
                    minute = time_match.group(3)
                    second = time_match.group(4)
                    
                    # 检查是否为整点（分钟为00，即 xx:00）
                    if minute == "00":
                        # 获取整行数据用于打印
                        row_data = {
                            'time': f"{date_str} {hour}:{minute}:{second} (UTC)",
                            'row_index': i + 1,
                            'page': current_page
                        }
                        
                        # 尝试获取文件名（通常在第一个或第二个单元格）
                        try:
                            if len(cells) > 1:
                                row_data['filename'] = cells[1].inner_text().strip()[:50]
                        except:
                            pass
                        
                        matched_data.append(row_data)
                        print(f"  ✓ 第{i+1}行 - 符合条件: {row_data['time']}", end="")
                        
                        # 定位并勾选复选框（优化速度）
                        checkbox = None
                        try:
                            checkbox = row.locator("input[type='checkbox']").first
                            if checkbox.count() == 0:
                                checkbox = row.locator("td").first.locator("input[type='checkbox']").first
                        except:
                            pass
                        
                        if checkbox and checkbox.count() > 0:
                            try:
                                # 使用JS直接设置checked属性（最快方式）
                                checkbox.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', { bubbles: true })); }")
                                page_checked += 1
                                total_checked += 1
                                print(" → 已勾选")
                            except:
                                try:
                                    checkbox.check(timeout=1000)
                                    page_checked += 1
                                    total_checked += 1
                                    print(" → 已勾选")
                                except:
                                    print(" ✗ 勾选失败")
                        else:
                            print(" ⚠ 未找到复选框")
                            
            except Exception as e:
                continue
        
        print(f"本页勾选: {page_checked} 个")
        
        # 翻到下一页（优化翻页逻辑 - 定位主表格的分页控件）
        if current_page < total_pages:
            try:
                # 等待页面稳定
                page.wait_for_timeout(500)
                
                # 先定位主表格的分页区域（通过"当前共有 X 页"文本）
                print("定位主表格的分页控件...")
                pagination_info = None
                try:
                    # 找到包含"当前共有 X 页"的分页信息区域
                    pagination_info = page.locator("text=/当前共有.*页/").first
                    if pagination_info.count() > 0:
                        # 滚动到分页区域，确保可见
                        pagination_info.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        print("已定位到主表格分页区域")
                    else:
                        print("未找到主表格分页信息")
                except Exception as e:
                    print(f"定位分页信息失败: {e}")
                
                # 在主表格的分页区域内查找"下一页"按钮
                next_button = None
                
                # 方法1: 通过表格定位分页控件（最可靠的方法）
                try:
                    # 找到主表格
                    table = page.locator("table").first
                    if table.count() > 0:
                        # 查找表格后面包含"当前共有"的分页区域
                        # 使用XPath查找紧跟在table后面的包含"当前共有"的元素
                        pagination_section = table.locator("xpath=following::*[contains(text(), '当前共有')][1]").first
                        
                        if pagination_section.count() > 0:
                            # 在该分页区域中查找"下一页"按钮
                            # 先尝试在分页区域内部查找所有"下一页"按钮
                            all_buttons_in_section = pagination_section.locator("a:has-text('下一页'), button:has-text('下一页')").all()
                            
                            if len(all_buttons_in_section) >= 2:
                                # 如果有多个，使用第二个
                                next_button = all_buttons_in_section[1]
                                print("通过表格定位到主表格的分页控件（使用第二个按钮）")
                            elif len(all_buttons_in_section) == 1:
                                # 如果只有一个，使用它
                                next_button = all_buttons_in_section[0]
                                print("通过表格定位到主表格的分页控件（使用第一个按钮）")
                            else:
                                # 如果找不到，查找紧跟在分页区域后面的"下一页"
                                next_button = pagination_section.locator("xpath=following::a[contains(text(), '下一页')][1]").first
                                if next_button.count() > 0:
                                    print("通过表格定位到分页区域后的'下一页'按钮")
                        else:
                            # 如果找不到分页区域，直接在表格后面查找所有"下一页"，使用第二个
                            all_buttons_after_table = table.locator("xpath=following::a[contains(text(), '下一页')]").all()
                            if len(all_buttons_after_table) >= 2:
                                next_button = all_buttons_after_table[1]
                                print("直接在表格后找到第二个'下一页'按钮")
                            elif len(all_buttons_after_table) == 1:
                                next_button = all_buttons_after_table[0]
                                print("直接在表格后找到第一个'下一页'按钮")
                except Exception as e:
                    print(f"方法1失败: {e}")
                
                # 方法2: 通过分页信息定位其父容器
                if (not next_button or next_button.count() == 0) and pagination_info and pagination_info.count() > 0:
                    try:
                        # 查找分页信息后面的所有"下一页"按钮
                        all_buttons_after_info = pagination_info.locator("xpath=following::a[contains(text(), '下一页')]").all()
                        
                        if len(all_buttons_after_info) >= 2:
                            # 如果有多个，使用第二个
                            next_button = all_buttons_after_info[1]
                            print("通过分页信息定位到第二个'下一页'按钮")
                        elif len(all_buttons_after_info) == 1:
                            # 如果只有一个，使用它
                            next_button = all_buttons_after_info[0]
                            print("通过分页信息定位到第一个'下一页'按钮")
                    except Exception as e:
                        print(f"方法2失败: {e}")
                
                # 方法3: 如果以上都失败，查找所有"下一页"并选择第二个（主表格的分页控件）
                if not next_button or next_button.count() == 0:
                    try:
                        all_next_buttons = page.locator("a:has-text('下一页'), button:has-text('下一页')").all()
                        print(f"找到 {len(all_next_buttons)} 个'下一页'按钮")
                        
                        if len(all_next_buttons) >= 2:
                            # 使用第二个按钮（主表格的分页控件）
                            next_button = all_next_buttons[1]
                            print(f"使用第二个'下一页'按钮（主表格的分页控件）")
                        elif len(all_next_buttons) == 1:
                            # 如果只有一个，也使用它
                            next_button = all_next_buttons[0]
                            print(f"只有一个'下一页'按钮，使用它")
                        else:
                            print("未找到任何'下一页'按钮")
                    except Exception as e:
                        print(f"查找所有'下一页'按钮失败: {e}")
                
                if next_button and next_button.count() > 0:
                    # 确保按钮可见
                    try:
                        next_button.scroll_into_view_if_needed()
                        page.wait_for_timeout(300)
                        
                        if next_button.is_visible(timeout=2000):
                            print(f"\n翻到第 {current_page + 1}/{total_pages} 页...")
                            
                            # 点击下一页按钮
                            next_button.click()
                            
                            # 等待页面加载完成
                            page.wait_for_load_state("networkidle")
                            page.wait_for_timeout(1500)
                            
                            # 验证表格已加载
                            page.wait_for_selector("table tbody tr", timeout=5000)
                            page.wait_for_timeout(500)
                            
                            # 滚动回顶部，准备处理新页面的数据
                            page.evaluate("window.scrollTo(0, 0)")
                            page.wait_for_timeout(300)
                            
                            current_page += 1
                        else:
                            print("'下一页'按钮不可见")
                            break
                    except Exception as e:
                        print(f"点击'下一页'按钮失败: {e}")
                        break
                else:
                    print(f"未找到主表格的'下一页'按钮，当前页: {current_page}/{total_pages}")
                    # 检查是否真的到了最后一页
                    if current_page >= total_pages:
                        print("已处理完所有页面")
                        break
                    else:
                        print("尝试继续...")
                        break
            except Exception as e:
                print(f"翻页失败: {e}")
                import traceback
                traceback.print_exc()
                break
        else:
            print(f"已处理完所有 {total_pages} 页")
            break
    
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
    
    # 关闭可能弹出的面板
    # try:
    #     page.get_by_role("button", name="关闭").click(timeout=2000)
    #     page.wait_for_timeout(500)
    # except:
    #     pass
    
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
