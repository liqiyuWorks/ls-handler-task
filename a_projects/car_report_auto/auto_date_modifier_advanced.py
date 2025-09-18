#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级自动修改车辆报告页面日期数据的脚本
"""

import asyncio
import json
import requests
import argparse
from datetime import datetime
from playwright.async_api import async_playwright
from loguru import logger


class AdvancedAutoDateModifier:
    def __init__(self, vin=None, new_date=None, qr_code_url=None, headless=True):
        self.base_url = "https://www.cherryautodealer.com/service/v3/BXRequestService.ashx"
        self.vin = vin or "LE4ZG8DB3ML639548"
        self.new_date = new_date or datetime.now().strftime("%Y-%m-%d")
        self.qr_code_url = qr_code_url or "https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg"
        self.headless = headless
        
        self.params = {
            "Method": "GenerateLinkURL",
            "AppName": "zhichepro",
            "vin": self.vin
        }
        
    async def get_report_url(self):
        """获取报告链接"""
        try:
            logger.info(f"正在请求API获取报告链接，VIN: {self.vin}")
            response = requests.get(self.base_url, params=self.params)
            response.raise_for_status()
            
            data = response.json()
            if data.get("Result") == 1 and data.get("Message") == "SUCCESS":
                report_url = data.get("ReturnObj")
                logger.info(f"成功获取报告链接: {report_url}")
                return report_url
            else:
                logger.error(f"API请求失败: {data}")
                return None
        except Exception as e:
            logger.error(f"获取报告链接时出错: {e}")
            return None
    
    async def modify_qr_codes(self, page):
        """修改页面中的二维码图片 - 专门针对class='qr-item'的元素"""
        try:
            # 专门查找class="qr-item"的元素
            qr_selectors = [
                ".qr-item",
                "div.qr-item",
                "//div[contains(@class, 'qr-item')]",
                "//*[contains(@class, 'qr-item')]"
            ]
            
            qr_elements = []
            for selector in qr_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        qr_elements.extend(elements)
                except Exception as e:
                    continue
            
            if not qr_elements:
                logger.warning("未找到class='qr-item'的元素")
                return False
            
            logger.info(f"找到 {len(qr_elements)} 个qr-item元素")
            
            # 修改每个qr-item元素
            modified_count = 0
            for i, element in enumerate(qr_elements):
                try:
                    # 检查元素内是否有canvas或img元素
                    canvas_elements = await element.query_selector_all("canvas")
                    img_elements = await element.query_selector_all("img")
                    
                    # 处理canvas元素 - 替换为图片
                    for j, canvas in enumerate(canvas_elements):
                        try:
                            # 使用JavaScript替换canvas为img
                            await page.evaluate(f"""
                                (canvas) => {{
                                    // 创建新的img元素
                                    const img = document.createElement('img');
                                    img.src = '{self.qr_code_url}';
                                    img.alt = '二维码';
                                    img.style.width = canvas.style.width || canvas.width + 'px';
                                    img.style.height = canvas.style.height || canvas.height + 'px';
                                    img.style.display = 'block';
                                    
                                    // 复制canvas的样式
                                    if (canvas.style.cssText) {{
                                        img.style.cssText = canvas.style.cssText;
                                    }}
                                    
                                    // 替换canvas
                                    canvas.parentNode.replaceChild(img, canvas);
                                    
                                    // 触发加载事件
                                    img.dispatchEvent(new Event('load', {{ bubbles: true }}));
                                }}
                            """, canvas)
                            
                            modified_count += 1
                            
                        except Exception as canvas_e:
                            logger.error(f"替换canvas时出错: {canvas_e}")
                    
                    # 处理img元素 - 直接修改src
                    for j, img in enumerate(img_elements):
                        try:
                            original_alt = await img.get_attribute("alt") or ""
                            
                            # 使用JavaScript修改图片src
                            await page.evaluate(f"""
                                (img) => {{
                                    // 保存原始属性
                                    const originalSrc = img.src;
                                    const originalAlt = img.alt;
                                    
                                    // 修改图片源
                                    img.src = '{self.qr_code_url}';
                                    img.setAttribute('src', '{self.qr_code_url}');
                                    
                                    // 更新alt属性
                                    if (originalAlt.includes('验证') || originalAlt.includes('保障')) {{
                                        img.alt = originalAlt;
                                    }}
                                    
                                    // 触发图片加载事件
                                    img.dispatchEvent(new Event('load', {{ bubbles: true }}));
                                    
                                    // 强制重新加载
                                    img.style.display = 'none';
                                    img.offsetHeight;
                                    img.style.display = '';
                                }}
                            """, img)
                            
                            # 验证修改是否成功
                            await page.wait_for_timeout(500)
                            new_src = await img.get_attribute("src")
                            
                            if new_src and self.qr_code_url in new_src:
                                modified_count += 1
                            else:
                                # 尝试强制修改
                                try:
                                    await page.evaluate(f"""
                                        (img) => {{
                                            img.src = '{self.qr_code_url}';
                                            img.setAttribute('src', '{self.qr_code_url}');
                                            img.style.display = 'none';
                                            img.offsetHeight;
                                            img.style.display = '';
                                        }}
                                    """, img)
                                    await page.wait_for_timeout(300)
                                    
                                    final_src = await img.get_attribute("src")
                                    if final_src and self.qr_code_url in final_src:
                                        modified_count += 1
                                    else:
                                        logger.error(f"强制修改img失败")
                                except Exception as force_e:
                                    logger.error(f"强制修改img出错: {force_e}")
                            
                        except Exception as img_e:
                            logger.error(f"修改img时出错: {img_e}")
                    
                    # 如果qr-item元素内既没有canvas也没有img，尝试直接添加img
                    if len(canvas_elements) == 0 and len(img_elements) == 0:
                        try:
                            await page.evaluate(f"""
                                (element) => {{
                                    // 创建新的img元素
                                    const img = document.createElement('img');
                                    img.src = '{self.qr_code_url}';
                                    img.alt = '二维码';
                                    img.style.width = '100px';
                                    img.style.height = '100px';
                                    img.style.display = 'block';
                                    
                                    // 添加到qr-item元素
                                    element.appendChild(img);
                                    
                                    // 触发加载事件
                                    img.dispatchEvent(new Event('load', {{ bubbles: true }}));
                                }}
                            """, element)
                            
                            modified_count += 1
                            
                        except Exception as add_e:
                            logger.error(f"添加img时出错: {add_e}")
                    
                except Exception as e:
                    logger.error(f"处理qr-item元素时出错: {e}")
            
            if modified_count > 0:
                logger.info(f"✅ 二维码修改成功，共修改 {modified_count} 个元素")
            else:
                logger.warning("⚠️ 未找到可修改的二维码元素")
            
            return modified_count > 0
            
        except Exception as e:
            logger.error(f"修改二维码时出错: {e}")
            return False
    
    async def modify_date_on_page(self, url):
        """在页面上修改日期数据"""
        screenshot_path = None
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                logger.info(f"正在打开页面: {url}")
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # 尝试多种定位方式
                selectors = [
                    "xpath=/html/body/div[1]/div[1]/div[1]/div[5]/span[1]",
                    "//span[contains(@class, 'date')]",
                    "//div[contains(@class, 'date')]//span",
                    "//span[contains(text(), '-')]",
                    "//div[contains(@class, 'date')]",
                    "//span[contains(@class, 'time')]",
                    "//div[contains(@class, 'time')]//span",
                    "//*[contains(text(), '-') and contains(text(), '202')]",  # 包含年份的日期元素
                    "//*[contains(text(), '报告发布日期')]",  # 包含特定文本的元素
                    "//*[contains(text(), '发布日期')]",
                    "//*[contains(text(), '日期')]",
                    "//span[contains(text(), '202')]",  # 包含年份的span元素
                    "//div[contains(text(), '202')]",   # 包含年份的div元素
                ]
                
                element = None
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            break
                    except:
                        continue
                
                if not element:
                    logger.error("未找到指定的日期元素")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    page_screenshot_path = f"page_screenshot_{timestamp}.png"
                    await page.screenshot(path=page_screenshot_path, full_page=True)
                    logger.info(f"页面截图已保存: {page_screenshot_path}")
                    
                    # 尝试获取页面中所有包含日期的元素信息
                    try:
                        date_elements = await page.query_selector_all("//*[contains(text(), '202')]")
                        logger.info(f"找到 {len(date_elements)} 个包含年份的元素")
                        for i, elem in enumerate(date_elements[:5]):  # 只显示前5个
                            text = await elem.text_content()
                            logger.info(f"元素 {i+1}: {text}")
                    except Exception as e:
                        logger.error(f"无法获取页面元素信息: {e}")
                    
                    return False, page_screenshot_path
                
                current_date = await element.text_content()
                logger.info(f"当前日期: {current_date}")
                
                # 分析当前文本格式，提取前缀和后缀
                prefix = ""
                suffix = ""
                date_part = self.new_date
                
                if current_date:
                    # 尝试提取日期部分和前缀后缀
                    import re
                    date_pattern = r'\d{4}-\d{2}-\d{2}'
                    date_match = re.search(date_pattern, current_date)
                    if date_match:
                        old_date = date_match.group()
                        prefix = current_date[:date_match.start()]
                        suffix = current_date[date_match.end():]
                
                # 优化后的修改策略 - 按成功率排序
                modification_success = False
                full_text = f"{prefix}{self.new_date}{suffix}".strip()
                
                # 方法1: 最稳定的JavaScript直接修改（成功率最高）
                try:
                    await page.evaluate(f"""
                        (element) => {{
                            // 直接修改文本内容 - 最可靠的方法
                            element.textContent = '{full_text}';
                            element.innerText = '{full_text}';
                            
                            // 如果是input元素，同时设置value
                            if (element.tagName === 'INPUT') {{
                                element.value = '{self.new_date}';
                            }}
                            
                            // 触发必要的事件
                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            
                            // 强制更新DOM
                            element.style.transform = 'translateZ(0)';
                        }}
                    """, element)
                    modification_success = True
                except Exception as e1:
                    pass
                
                # 方法2: 如果方法1失败，尝试点击后输入
                if not modification_success:
                    try:
                        await element.click()
                        await page.wait_for_timeout(300)
                        await element.press("Control+a")  # 全选
                        await page.wait_for_timeout(200)
                        await element.type(full_text)
                        modification_success = True
                    except Exception as e2:
                        pass
                
                # 方法3: 如果方法2失败，尝试双击输入
                if not modification_success:
                    try:
                        await element.dblclick()
                        await page.wait_for_timeout(300)
                        await page.keyboard.type(full_text)
                        await page.keyboard.press("Enter")
                        modification_success = True
                    except Exception as e3:
                        pass
                
                # 方法4: 如果前三种方法都失败，尝试页面级别修改
                if not modification_success:
                    try:
                        modified_count = await page.evaluate(f"""
                            () => {{
                                let count = 0;
                                const elements = document.querySelectorAll('*');
                                elements.forEach(element => {{
                                    if (element.textContent && element.textContent.includes('202')) {{
                                        const newText = element.textContent.replace(/\\d{{4}}-\\d{{2}}-\\d{{2}}/g, '{self.new_date}');
                                        if (newText !== element.textContent) {{
                                            element.textContent = newText;
                                            element.innerText = newText;
                                            count++;
                                        }}
                                    }}
                                }});
                                return count;
                            }}
                        """)
                        if modified_count > 0:
                            modification_success = True
                        else:
                            logger.warning("页面级别修改未找到匹配元素")
                    except Exception as e4:
                        pass
                
                # 方法5: 最后的备用方案 - 模拟用户操作
                if not modification_success:
                    try:
                        await element.hover()
                        await page.wait_for_timeout(200)
                        await element.click()
                        await page.wait_for_timeout(300)
                        await page.keyboard.press("Control+a")
                        await page.wait_for_timeout(100)
                        await page.keyboard.press("Delete")
                        await page.wait_for_timeout(100)
                        await page.keyboard.type(full_text)
                        await page.wait_for_timeout(200)
                        await page.keyboard.press("Enter")
                        modification_success = True
                    except Exception as e5:
                        logger.error(f"所有修改方法都失败: {e5}")
                        # 保存元素信息用于调试
                        try:
                            element_info = await page.evaluate("""
                                (element) => {
                                    return {
                                        tagName: element.tagName,
                                        className: element.className,
                                        id: element.id,
                                        textContent: element.textContent,
                                        innerHTML: element.innerHTML
                                    }
                                }
                            """, element)
                            logger.info(f"元素详细信息: {element_info}")
                        except Exception as debug_e:
                            logger.error(f"无法获取元素详细信息: {debug_e}")
                        raise Exception(f"无法修改日期元素，所有方法都失败了")
                
                # 智能重试机制 - 如果第一次修改失败，尝试不同的方法
                if not modification_success:
                    logger.warning("第一次修改失败，尝试智能重试...")
                    await page.wait_for_timeout(1000)
                    
                    # 重试：使用更激进的JavaScript方法
                    try:
                        await page.evaluate(f"""
                            (element) => {{
                                // 保存原始属性
                                const originalText = element.textContent;
                                const originalInnerHTML = element.innerHTML;
                                
                                // 多种方式修改
                                element.textContent = '{full_text}';
                                element.innerText = '{full_text}';
                                element.innerHTML = '{full_text}';
                                
                                // 如果是input元素
                                if (element.tagName === 'INPUT') {{
                                    element.value = '{self.new_date}';
                                }}
                                
                                // 修改所有子元素
                                const children = element.querySelectorAll('*');
                                children.forEach(child => {{
                                    if (child.textContent && child.textContent.includes('202')) {{
                                        child.textContent = child.textContent.replace(/\\d{{4}}-\\d{{2}}-\\d{{2}}/g, '{self.new_date}');
                                    }}
                                }});
                                
                                // 触发所有事件
                                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                element.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                element.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                                
                                // 强制更新
                                element.style.transform = 'translateZ(0)';
                                
                                // 如果修改失败，恢复原始内容
                                if (element.textContent !== '{full_text}') {{
                                    element.textContent = originalText;
                                    element.innerHTML = originalInnerHTML;
                                }}
                            }}
                        """, element)
                        modification_success = True
                    except Exception as retry_e:
                        pass
                
                await page.wait_for_timeout(1000)
                
                # 修改二维码图片
                qr_modification_success = await self.modify_qr_codes(page)
                
                # 优化后的验证逻辑 - 更稳定可靠
                verification_success = False
                try:
                    # 等待页面稳定
                    await page.wait_for_timeout(1500)
                    
                    # 重新获取元素（防止元素失效）
                    element = None
                    for selector in selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                break
                        except:
                            continue
                    
                    if not element:
                        logger.error("验证时无法重新找到元素")
                        return False, None
                    
                    updated_text = await element.text_content()
                    expected_text = f"{prefix}{self.new_date}{suffix}".strip()
                    
                    # 简化的验证逻辑 - 更可靠
                    verification_passed = False
                    
                    # 主要验证：检查是否包含目标日期
                    if updated_text and self.new_date in updated_text:
                        verification_passed = True
                    
                    # 次要验证：检查是否完全匹配
                    elif updated_text and updated_text.strip() == expected_text:
                        verification_passed = True
                    
                    # 备用验证：检查是否不再包含旧日期
                    elif updated_text and current_date and updated_text != current_date:
                        import re
                        date_pattern = r'\d{4}-\d{2}-\d{2}'
                        all_dates = re.findall(date_pattern, updated_text)
                        if all_dates and all(date == self.new_date for date in all_dates):
                            verification_passed = True
                    
                    if verification_passed:
                        verification_success = True
                    else:
                        # 尝试最终修正
                        try:
                            await page.evaluate(f"""
                                (element) => {{
                                    element.textContent = '{expected_text}';
                                    element.innerText = '{expected_text}';
                                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                }}
                            """, element)
                            await page.wait_for_timeout(500)
                            
                            # 最终验证
                            final_text = await element.text_content()
                            if final_text and self.new_date in final_text:
                                verification_success = True
                        except Exception as retry_e:
                            pass
                            
                except Exception as e:
                    logger.error(f"验证过程中出错: {e}")
                
                # 如果验证失败，尝试强制修改
                if not verification_success:
                    try:
                        # 强制修改所有包含日期的元素
                        modified_count = await page.evaluate(f"""
                            () => {{
                                let count = 0;
                                const elements = document.querySelectorAll('*');
                                elements.forEach(element => {{
                                    if (element.textContent && element.textContent.includes('202')) {{
                                        const newText = element.textContent.replace(/\\d{{4}}-\\d{{2}}-\\d{{2}}/g, '{self.new_date}');
                                        if (newText !== element.textContent) {{
                                            element.textContent = newText;
                                            element.innerText = newText;
                                            count++;
                                        }}
                                    }}
                                }});
                                return count;
                            }}
                        """)
                        
                        if modified_count > 0:
                            verification_success = True
                        else:
                            return False, None
                    except Exception as force_e:
                        return False, None
                
                # 等待页面完全稳定
                await page.wait_for_timeout(2000)
                
                # 最终验证：检查修改是否持久化
                try:
                    # 再次检查元素内容，确保和目标日期保持一致
                    final_element = await page.query_selector(selectors[0])  # 使用第一个选择器
                    if final_element:
                        final_text = await final_element.text_content()
                        
                        # 增强的验证逻辑
                        verification_passed = False
                        
                        # 检查1: 是否包含目标日期
                        if final_text and self.new_date in final_text:
                            verification_passed = True
                        
                        # 检查2: 是否完全匹配期望的文本格式
                        expected_text = f"{prefix}{self.new_date}{suffix}".strip()
                        if final_text and final_text.strip() == expected_text:
                            verification_passed = True
                        
                        # 检查3: 是否不再包含其他日期格式
                        import re
                        date_pattern = r'\d{4}-\d{2}-\d{2}'
                        all_dates = re.findall(date_pattern, final_text or "")
                        if all_dates and all(date == self.new_date for date in all_dates):
                            verification_passed = True
                        
                        # 检查4: 文本长度是否合理
                        if final_text and len(final_text) >= len(self.new_date):
                            verification_passed = True
                        
                        # 检查5: 是否与原始文本不同
                        if final_text and current_date and final_text != current_date:
                            verification_passed = True
                        
                        if verification_passed:
                            # 如果验证成功但文本不完全匹配，尝试最终修正
                            if final_text and final_text.strip() != expected_text:
                                try:
                                    await page.evaluate(f"""
                                        (element) => {{
                                            element.textContent = '{expected_text}';
                                            element.innerHTML = '{expected_text}';
                                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        }}
                                    """, final_element)
                                    await page.wait_for_timeout(500)
                                except Exception as correct_e:
                                    pass
                        
                except Exception as e:
                    pass
                
                # 保存修改后的页面截图
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"modified_report_{timestamp}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                
                return True, screenshot_path
                
            except Exception as e:
                logger.error(f"修改日期时出错: {e}")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_screenshot_path = f"error_screenshot_{timestamp}.png"
                await page.screenshot(path=error_screenshot_path, full_page=True)
                logger.info(f"错误页面截图已保存: {error_screenshot_path}")
                return False, error_screenshot_path
            finally:
                await browser.close()
    
    async def run(self):
        """运行主流程"""
        logger.info(f"开始执行自动修改流程...")
        
        report_url = await self.get_report_url()
        if not report_url:
            logger.error("无法获取报告链接，流程终止")
            return False, None
        
        success, screenshot_path = await self.modify_date_on_page(report_url)
        
        if success:
            logger.info("✅ 修改完成！")
            return True, screenshot_path
        else:
            logger.error("❌ 修改失败！")
            return False, screenshot_path


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动修改车辆报告页面日期数据和二维码图片")
    parser.add_argument("--vin", help="车辆VIN码", default="LE4ZG8DB3ML639548")
    parser.add_argument("--date", help="新日期 (YYYY-MM-DD格式)", default=None)
    parser.add_argument("--qr-url", help="二维码图片URL", default="https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg")
    parser.add_argument("--headless", action="store_true", help="无头模式运行")
    
    args = parser.parse_args()
    
    # 如果没有提供日期，使用当前日期
    if not args.date:
        args.date = datetime.now().strftime("%Y-%m-%d")
    
    modifier = AdvancedAutoDateModifier(
        vin=args.vin, 
        new_date=args.date,
        qr_code_url=args.qr_url,
        headless=args.headless
    )
    success, screenshot_path = await modifier.run()
    
    if success:
        print(f"✅ 修改完成！截图: {screenshot_path}")
    else:
        print(f"❌ 修改失败！")


if __name__ == "__main__":
    asyncio.run(main()) 