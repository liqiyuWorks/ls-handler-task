#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆报告修改Web界面 - Redis优化版本
"""

from flask import Flask, render_template, request, jsonify
import asyncio
import json
import requests
from datetime import datetime
from playwright.async_api import async_playwright
from loguru import logger
import threading
import os
import tempfile
import shutil
from playwright_config import PlaywrightConfig
from redis_task_manager import get_redis_task_manager, init_redis_task_manager

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(current_dir, 'templates'),
            static_folder=os.path.join(current_dir, 'static'))

# 初始化Redis任务管理器
redis_task_manager = None

class CarReportModifier:
    def __init__(self, vin, new_date=None, qr_code_url=None, headless=True):
        self.base_url = "https://www.cherryautodealer.com/service/v3/BXRequestService.ashx"
        self.vin = vin
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
            # 优先尝试第一个接口获取报告链接
            alt_base_url = "https://cxm.yimuzhiche.com/service/CustomerService.ashx"
            alt_params = {
                "Method": "GenerateLinkURL",
                "AppName": "zhichepro",
                "vin": self.vin
            }
            try:
                logger.info(f"尝试API接口获取报告链接，VIN: {self.vin}")
                alt_response = requests.get(alt_base_url, params=alt_params, timeout=10)
                alt_response.raise_for_status()
                alt_data = alt_response.json()
                if alt_data.get("Result") == 1 and alt_data.get("Message") == "获取成功":
                    report_url = alt_data.get("ReturnObj")
                    logger.info(f"API接口成功获取报告链接: {report_url}")
                    return report_url
                else:
                    logger.warning(f"API接口未成功: {alt_data}")
            except Exception as e:
                logger.warning(f"API接口请求失败: {e}")
            
            logger.info(f"正在请求APP获取报告链接，VIN: {self.vin}")
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
    
    async def modify_date_on_page(self, url):
        """在页面上修改日期数据 - Docker 优化版本"""
        try:
            async with PlaywrightConfig(headless=self.headless) as config:
                # 导航到页面
                if not await config.navigate_to_page(url):
                    return False, await config.take_screenshot("page_load_error")
                
                # 🚀 优化：按优先级排序，高效的选择器在前
                selectors = [
                    "xpath=/html/body/div[1]/div[1]/div[1]/div[5]/span[1]",  # 最精确的路径
                    "//*[contains(text(), '-') and contains(text(), '202')]",  # 包含日期格式的元素
                    "//span[contains(@class, 'date')]",
                    "//span[contains(text(), '202')]",  # 包含年份的span
                    "//*[contains(text(), '报告发布日期')]",
                    "//div[contains(@class, 'date')]//span",
                    "//span[contains(@class, 'time')]",
                ]
                
                # 查找日期元素
                element = await config.find_element(selectors)
                
                if not element:
                    logger.error("未找到指定的日期元素")
                    return False, await config.take_screenshot("no_date_element")
                
                current_date = await element.text_content()
                logger.info(f"当前日期: {current_date}")
                
                # 分析当前文本格式，提取前缀和后缀
                prefix = ""
                suffix = ""
                date_part = self.new_date
                
                if current_date:
                    import re
                    date_pattern = r'\d{4}-\d{2}-\d{2}'
                    date_match = re.search(date_pattern, current_date)
                    if date_match:
                        old_date = date_match.group()
                        prefix = current_date[:date_match.start()]
                        suffix = current_date[date_match.end():]
                        logger.info(f"日期格式分析 - 前缀: '{prefix}', 新日期: '{self.new_date}', 后缀: '{suffix}'")
                
                full_text = f"{prefix}{self.new_date}{suffix}".strip()
                
                # 修改日期
                modification_success = await config.modify_element_text(element, full_text)
                
                if not modification_success:
                    return False, await config.save_element_as_image('//*[@id="reportRef"]', "date_modification_failed")
                
                # 🚀 优化：减少等待时间，并行处理
                logger.info("⚡ 开始快速展开和截图流程...")
                
                # 1. 先等待页面基本稳定（减少等待时间）
                await config.page.wait_for_timeout(1500)
                
                # 2. 快速展开操作
                await self.expand_all_details_optimized(config)
                
                # 简单等待网络稳定
                try:
                    await config.page.wait_for_load_state('networkidle', timeout=5000)
                except:
                    pass  # 如果网络等待超时，继续执行
                
                # 3. 替换二维码
                logger.info("🔄 开始替换页面中的二维码...")
                qr_modification_success = await self.modify_qr_codes(config)
                if qr_modification_success:
                    logger.info("✅ 二维码替换成功")
                else:
                    logger.warning("⚠️ 二维码替换失败或无二维码需要替换")
                
                # 4. 快速准备截图（优化版本）
                await self.prepare_for_screenshot_optimized(config)
                
                # 5. 直接截图（移除冗余检查）
                logger.info("📸 执行快速截图...")
                screenshot_path = await config.save_element_as_image_optimized('//*[@id="reportRef"]', "modified_report")
                
                return True, screenshot_path
                
        except Exception as e:
            logger.error(f"修改日期时出错: {e}")
            return False, None
    
    async def expand_all_details_optimized(self, config):
        """优化版本：快速展开详情按钮"""
        try:
            logger.info("⚡ 快速展开详情按钮...")
            
            # 🚀 优化：使用更精确的选择器，减少查找时间
            priority_selectors = [
                "//span[contains(text(), '展开详情')]",
                "//span[contains(text(), '展开') and not(contains(text(), '折叠完整解析'))]",
                '//*[@id="van-tab-2"]//span[contains(text(), "展开")]',
            ]
            
            expanded_count = 0
            
            for selector in priority_selectors:
                try:
                    # 快速查找，短超时
                    elements = await config.page.locator(selector).all()
                    
                    for element in elements:
                        try:
                            if await element.is_visible() and await element.is_enabled():
                                text_content = await element.text_content()
                                
                                # 快速排除检查
                                if text_content and any(keyword in text_content for keyword in ["折叠完整解析", "完整解析"]):
                                    continue
                                
                                # 快速点击，减少等待
                                await element.click()
                                expanded_count += 1
                                
                                # 🚀 优化：减少等待时间
                                await config.page.wait_for_timeout(300)
                                
                        except Exception:
                            continue
                            
                except Exception:
                    continue
            
            logger.info(f"⚡ 快速展开完成，共展开 {expanded_count} 个按钮")
            return True
            
        except Exception as e:
            logger.error(f"快速展开失败: {e}")
            return False
    
    async def prepare_for_screenshot_optimized(self, config):
        """优化版本：快速准备截图"""
        try:
            logger.info("⚡ 快速准备截图...")
            
            # 🚀 并行执行滚动和样式设置
            scroll_task = config.page.evaluate("window.scrollTo(0, 0)")
            style_task = config.page.add_style_tag(content="""
                *, *::before, *::after {
                    animation-duration: 0s !important;
                    transition-duration: 0s !important;
                }
            """)
            
            await scroll_task
            await style_task
            
            # 简短等待确保生效
            await config.page.wait_for_timeout(500)
            
        except Exception as e:
            logger.warning(f"准备截图时出错: {e}")
    
    async def expand_all_details(self, config):
        """查找并点击所有"展开详情"按钮，但排除"折叠完整解析"按钮"""
        try:
            logger.info("开始查找并展开详情按钮（排除折叠完整解析）...")
            
            # 定义多种可能的"展开详情"按钮选择器
            expand_selectors = [
                # 基于提供的参考路径
                '//*[@id="van-tab-2"]/div[4]/div/div[2]/div[2]/span',
                # 通用的展开详情选择器
                "//span[contains(text(), '展开详情')]",
                "//span[contains(text(), '展开')]",
                "//span[contains(text(), '详情')]",
                "//button[contains(text(), '展开详情')]",
                "//div[contains(text(), '展开详情')]",
                "//a[contains(text(), '展开详情')]",
                # 基于class的选择器
                "//span[contains(@class, 'expand')]",
                "//span[contains(@class, 'detail')]",
                "//span[contains(@class, 'more')]",
                "//button[contains(@class, 'expand')]",
                "//div[contains(@class, 'expand')]",
                # 通过icon或符号查找
                "//span[contains(text(), '▼')]",
                "//span[contains(text(), '▽')]",
                "//span[contains(text(), '⌄')]",
                "//span[contains(text(), '↓')]",
                "//span[contains(text(), '更多')]",
                "//span[contains(text(), '查看更多')]",
                "//span[contains(text(), '查看详情')]",
                # van-ui 相关选择器
                "//*[contains(@id, 'van-tab')]//span[contains(text(), '展开')]",
                "//*[contains(@id, 'van-tab')]//span[contains(text(), '详情')]",
                "//*[contains(@class, 'van-')]//span[contains(text(), '展开')]",
            ]
            
            expanded_count = 0
            total_attempts = 0
            
            # 尝试查找所有可能的展开按钮
            for selector in expand_selectors:
                try:
                    # 查找所有匹配的元素
                    elements = await config.page.locator(selector).all()
                    
                    if elements:
                        logger.info(f"找到 {len(elements)} 个匹配选择器 '{selector}' 的元素")
                        
                        for i, element in enumerate(elements):
                            try:
                                # 检查元素是否可见和可点击
                                is_visible = await element.is_visible()
                                is_enabled = await element.is_enabled()
                                
                                if is_visible and is_enabled:
                                    # 获取元素文本内容
                                    text_content = await element.text_content()
                                    
                                    # 🚫 排除"折叠完整解析"按钮
                                    if text_content and "折叠完整解析" in text_content:
                                        logger.info(f"跳过折叠完整解析按钮: '{text_content}'")
                                        continue
                                    
                                    # 🚫 也排除包含"完整解析"的其他相关按钮
                                    if text_content and any(keyword in text_content for keyword in ["完整解析", "折叠完整", "隐藏完整"]):
                                        logger.info(f"跳过完整解析相关按钮: '{text_content}'")
                                        continue
                                    
                                    logger.info(f"尝试点击元素 {i+1}: '{text_content}'")
                                    
                                    # 滚动到元素位置
                                    await element.scroll_into_view_if_needed()
                                    await config.page.wait_for_timeout(500)
                                    
                                    # 尝试点击
                                    await element.click()
                                    expanded_count += 1
                                    total_attempts += 1
                                    
                                    # 等待页面响应
                                    await config.page.wait_for_timeout(1000)
                                    
                                    logger.info(f"✅ 成功点击展开按钮: '{text_content}'")
                                else:
                                    logger.debug(f"元素不可见或不可点击: visible={is_visible}, enabled={is_enabled}")
                                    
                            except Exception as e:
                                logger.warning(f"点击第 {i+1} 个元素时出错: {e}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 查找失败: {e}")
                    continue
            
            # 验证展开操作是否成功
            success_validated = await self.validate_expansion_success(config)
            
            if expanded_count > 0:
                logger.info(f"✅ 成功展开了 {expanded_count} 个详情按钮（已排除折叠完整解析），验证结果: {success_validated}")
                return True
            else:
                logger.warning("⚠️ 未找到任何可点击的展开详情按钮（排除折叠完整解析后）")
                # 保存当前页面截图用于调试
                await config.take_screenshot("no_expand_buttons_found")
                return False
                
        except Exception as e:
            logger.error(f"展开详情时出错: {e}")
            return False
    
    async def validate_expansion_success(self, config):
        """验证展开操作是否成功"""
        try:
            logger.info("验证展开操作是否成功...")
            
            # 定义用于验证展开成功的选择器
            validation_selectors = [
                # 查找可能的收起按钮或已展开状态的指示器
                "//span[contains(text(), '收起')]",
                "//span[contains(text(), '折叠')]",
                "//span[contains(text(), '▲')]",
                "//span[contains(text(), '△')]",
                "//span[contains(text(), '⌃')]",
                "//span[contains(text(), '↑')]",
                "//span[contains(text(), '收起详情')]",
                # 查找展开后可能出现的详细内容
                "//div[contains(@class, 'detail') and contains(@class, 'expanded')]",
                "//div[contains(@class, 'content') and contains(@class, 'show')]",
                "//div[contains(@style, 'display: block')]",
                "//div[contains(@class, 'van-collapse-item') and contains(@class, 'van-collapse-item--expanded')]",
            ]
            
            validation_count = 0
            
            for selector in validation_selectors:
                try:
                    elements = await config.page.locator(selector).all()
                    if elements:
                        visible_elements = []
                        for element in elements:
                            if await element.is_visible():
                                visible_elements.append(element)
                        
                        if visible_elements:
                            validation_count += len(visible_elements)
                            logger.info(f"验证选择器 '{selector}' 找到 {len(visible_elements)} 个可见元素")
                            
                except Exception as e:
                    logger.debug(f"验证选择器 '{selector}' 查找失败: {e}")
                    continue
            
            # 额外验证：比较展开前后页面高度变化
            try:
                page_height = await config.page.evaluate("document.body.scrollHeight")
                logger.info(f"当前页面高度: {page_height}px")
                
                # 如果页面有较大高度，可能说明内容已展开
                if page_height > 2000:  # 假设展开后页面会变高
                    validation_count += 1
                    logger.info("页面高度增加，可能表示内容已展开")
                    
            except Exception as e:
                logger.debug(f"检查页面高度失败: {e}")
            
            if validation_count > 0:
                logger.info(f"✅ 展开验证成功，找到 {validation_count} 个验证指标")
                return True
            else:
                logger.warning("⚠️ 无法验证展开是否成功")
                return False
                
        except Exception as e:
            logger.error(f"验证展开成功时出错: {e}")
            return False
    
    async def modify_qr_codes(self, config):
        """修改页面中的二维码图片 - 专门针对class='qrcode'和class='qr-item'的元素"""
        try:
            logger.info("🔄 开始替换页面中的二维码...")
            
            # 等待页面完全加载
            await config.page.wait_for_timeout(2000)
            
            # 查找class="qrcode"和class="qr-item"的元素
            qr_selectors = [
                ".qr-item",  # 优先使用最精确的选择器
                "div.qr-item",
                ".qrcode",
                "div.qrcode",
                "//div[contains(@class, 'qr-item')]",
                "//div[contains(@class, 'qrcode')]",
                "//*[contains(@class, 'qr-item')]",
                "//*[contains(@class, 'qrcode')]"
            ]
            
            # 添加调试：先检查页面中所有可能的二维码相关元素
            logger.info("🔍 开始搜索页面中的二维码元素...")
            try:
                # 使用JavaScript查找所有可能的二维码元素
                all_qr_elements = await config.page.evaluate("""
                    () => {
                        const elements = [];
                        
                        // 查找所有包含qr相关class的元素
                        document.querySelectorAll('*').forEach(el => {
                            const className = el.className || '';
                            if (typeof className === 'string' && 
                                (className.includes('qr') || className.includes('code') || className.includes('QR'))) {
                                elements.push({
                                    tagName: el.tagName,
                                    className: className,
                                    id: el.id || '',
                                    textContent: el.textContent?.substring(0, 50) || ''
                                });
                            }
                        });
                        
                        return elements;
                    }
                """)
                
                if all_qr_elements:
                    logger.info(f"🔍 找到 {len(all_qr_elements)} 个可能相关的元素:")
                    for i, elem in enumerate(all_qr_elements[:10]):  # 只显示前10个
                        logger.info(f"  元素 {i+1}: {elem['tagName']}, class='{elem['className']}', id='{elem['id']}', text='{elem['textContent']}'")
                else:
                    logger.warning("🔍 未找到任何包含qr相关class的元素")
                    
            except Exception as e:
                logger.debug(f"搜索页面元素时出错: {e}")
            
            qr_elements = []
            for selector in qr_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath选择器
                        elements = await config.page.locator(selector).all()
                    else:
                        # CSS选择器
                        elements = await config.page.locator(selector).all()
                    
                    if elements:
                        qr_elements.extend(elements)
                        logger.info(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
                        
                        # 不要停止查找，收集所有选择器找到的元素
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 查找失败: {e}")
                    continue
            
            # 去重并确保所有元素都被处理
            qr_elements = list(set(qr_elements))
            logger.info(f"🔍 总共找到 {len(qr_elements)} 个唯一的二维码容器元素")
            
            # 如果使用选择器没有找到元素，尝试使用JavaScript直接查找
            if not qr_elements:
                logger.info("🔍 选择器未找到元素，尝试使用JavaScript直接查找...")
                try:
                    js_result = await config.page.evaluate("""
                        () => {
                            const elements = [];
                            
                            // 查找所有包含qr-item或qrcode class的元素
                            document.querySelectorAll('.qr-item, .qrcode').forEach(el => {
                                elements.push({
                                    element: el,
                                    className: el.className || '',
                                    hasCanvas: !!el.querySelector('canvas'),
                                    hasImg: !!el.querySelector('img'),
                                    textContent: el.textContent?.substring(0, 100) || ''
                                });
                            });
                            
                            return elements.length;
                        }
                    """)
                    
                    if js_result > 0:
                        logger.info(f"🔍 JavaScript找到 {js_result} 个二维码容器")
                        # 重新使用JavaScript查找元素
                        qr_elements = await config.page.locator(".qr-item, .qrcode").all()
                    else:
                        logger.warning("🔍 JavaScript也未找到二维码容器")
                        
                except Exception as e:
                    logger.debug(f"JavaScript查找失败: {e}")
            
            if not qr_elements:
                logger.warning("未找到class='qrcode'或class='qr-item'的元素")
                
                # 尝试查找页面中的所有元素，看看是否有其他二维码相关的元素
                all_elements = await config.page.locator("*").all()
                qr_related = []
                for elem in all_elements[:100]:  # 只检查前100个元素
                    try:
                        class_attr = await elem.get_attribute("class")
                        if class_attr and ("qr" in class_attr.lower() or "code" in class_attr.lower()):
                            qr_related.append(elem)
                    except:
                        continue
                
                if qr_related:
                    logger.info(f"找到 {len(qr_related)} 个可能相关的元素: {[await elem.get_attribute('class') for elem in qr_related[:5]]}")
                
                return False
            
            # 去重
            qr_elements = list(set(qr_elements))
            logger.info(f"找到 {len(qr_elements)} 个二维码容器元素")
            
            # 调试：打印每个元素的详细信息
            for i, elem in enumerate(qr_elements[:3]):  # 只检查前3个
                try:
                    class_attr = await elem.get_attribute("class")
                    inner_html = await elem.inner_html()
                    logger.info(f"元素 {i+1}: class='{class_attr}', 内容长度: {len(inner_html)}")
                except Exception as e:
                    logger.debug(f"无法获取元素 {i+1} 信息: {e}")
            
            # 构建本地图片路径
            local_qr_path = os.path.join(current_dir, "getQRCode.jpg")
            if not os.path.exists(local_qr_path):
                logger.error(f"本地二维码图片不存在: {local_qr_path}")
                return False
            
            # 将图片转换为base64编码，避免file://协议问题
            try:
                import base64
                with open(local_qr_path, 'rb') as img_file:
                    img_data = img_file.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    file_url = f"data:image/jpeg;base64,{img_base64}"
                    logger.info(f"成功将图片转换为base64编码，长度: {len(img_base64)} 字符")
            except Exception as e:
                logger.error(f"转换图片为base64失败: {e}")
                # 回退到file://协议
                if os.name == 'nt':  # Windows
                    file_url = f"file:///{local_qr_path.replace(os.sep, '/')}"
                else:  # macOS/Linux
                    file_url = f"file://{local_qr_path}"
                logger.warning(f"回退到file://协议: {file_url}")
            
            logger.info(f"使用图片URL: {file_url[:100]}...")
            logger.info(f"原始路径: {local_qr_path}")
            logger.info(f"操作系统: {os.name}")
            
            # 验证图片文件
            try:
                import PIL.Image
                with PIL.Image.open(local_qr_path) as img:
                    width, height = img.size
                    logger.info(f"图片尺寸: {width}x{height} 像素")
            except Exception as e:
                logger.warning(f"无法读取图片信息: {e}")
            
            # 修改每个二维码容器元素
            modified_count = 0
            for i, element in enumerate(qr_elements):
                try:
                    # 检查元素内是否有canvas或img元素
                    # 使用locator来查找子元素
                    canvas_elements = await element.locator("canvas").all()
                    img_elements = await element.locator("img").all()
                    
                    logger.info(f"处理第 {i+1} 个二维码容器，找到 {len(canvas_elements)} 个canvas，{len(img_elements)} 个img")
                    
                    # 如果找到img元素，检查是否已经是我们的目标图片
                    has_target_image = False
                    if len(img_elements) > 0:
                        for img_idx, img in enumerate(img_elements):
                            try:
                                img_src = await img.get_attribute("src")
                                if img_src and file_url in img_src:
                                    logger.info(f"第 {i+1} 个容器的第 {img_idx+1} 个img已经是目标图片: {img_src}")
                                    has_target_image = True
                                    break
                                else:
                                    logger.info(f"第 {i+1} 个容器的第 {img_idx+1} 个img的src: {img_src}")
                            except Exception as e:
                                logger.debug(f"无法获取img src: {e}")
                    
                    # 如果容器已经有目标图片，记录但继续处理其他容器
                    if has_target_image:
                        logger.info(f"第 {i+1} 个容器已包含目标图片，但继续处理其他容器...")
                    
                    logger.info(f"🔄 继续处理第 {i+1} 个二维码容器...")
                    
                    # 调试：检查元素的HTML内容
                    try:
                        element_html = await element.inner_html()
                        logger.info(f"第 {i+1} 个二维码容器的HTML内容: {element_html[:200]}...")
                    except Exception as e:
                        logger.debug(f"无法获取第 {i+1} 个元素的HTML内容: {e}")
                    
                    # 强制处理：即使容器已经有目标图片，也要确保所有canvas都被替换
                    force_process = has_target_image and len(canvas_elements) > 0
                    if force_process:
                        logger.info(f"🔧 强制处理第 {i+1} 个容器，确保所有canvas都被替换...")
                    
                    # 如果没有找到canvas或img，尝试直接查找
                    if len(canvas_elements) == 0 and len(img_elements) == 0:
                        logger.info(f"第 {i+1} 个容器内没有找到canvas或img，尝试直接查找...")
                        # 尝试使用更宽泛的选择器
                        all_canvas = await config.page.locator("canvas").all()
                        all_img = await config.page.locator("img").all()
                        logger.info(f"页面中共有 {len(all_canvas)} 个canvas，{len(all_img)} 个img")
                        
                        # 检查是否有canvas在页面中但不在当前容器中
                        for canvas in all_canvas:
                            try:
                                canvas_parent = await canvas.locator("xpath=..").first()
                                if canvas_parent:
                                    parent_class = await canvas_parent.get_attribute("class")
                                    if parent_class and "qr" in parent_class.lower():
                                        logger.info(f"找到可能相关的canvas，父元素class: {parent_class}")
                            except:
                                continue
                    
                    # 处理canvas元素 - 替换为图片
                    for j, canvas in enumerate(canvas_elements):
                        try:
                            logger.info(f"🔄 处理第 {i+1} 个容器的第 {j+1} 个canvas元素...")
                            
                            # 使用更可靠的方法替换canvas为img
                            # 通过选择器直接查找和替换，避免元素传递问题
                            canvas_selector = f"canvas:nth-of-type({j+1})"
                            
                            # 在页面上直接执行替换 - 修复：限制在特定容器内
                            result = await config.page.evaluate(f"""
                                () => {{
                                    try {{
                                        // 查找第 {i+1} 个qr-item容器
                                        const qrContainers = document.querySelectorAll('.qr-item');
                                        if (qrContainers.length === 0) {{
                                            return {{ success: false, error: 'no qr-item containers found' }};
                                        }}
                                        
                                        const container = qrContainers[{i}];
                                        if (!container) {{
                                            return {{ success: false, error: 'container not found' }};
                                        }}
                                        
                                        // 在容器内查找canvas元素
                                        const canvas = container.querySelector('canvas');
                                        if (!canvas) {{
                                            return {{ success: false, error: 'canvas not found in container' }};
                                        }}
                                        
                                        // 获取canvas的尺寸
                                        const width = canvas.width || canvas.offsetWidth || 60;
                                        const height = canvas.height || canvas.offsetHeight || 60;
                                        
                                        // 创建新的img元素
                                        const img = document.createElement('img');
                                        img.src = '{file_url}';
                                        img.alt = '二维码';
                                        img.style.width = width + 'px';
                                        img.style.height = height + 'px';
                                        img.style.display = 'block';
                                        
                                        // 复制canvas的样式
                                        if (canvas.style.cssText) {{
                                            img.style.cssText = canvas.style.cssText;
                                        }}
                                        
                                        // 替换canvas
                                        if (canvas.parentNode) {{
                                            canvas.parentNode.replaceChild(img, canvas);
                                            
                                            // 触发加载事件
                                            img.dispatchEvent(new Event('load', {{ bubbles: true }}));
                                            
                                            // 验证图片是否正确加载
                                            setTimeout(() => {{
                                                if (img.complete && img.naturalWidth > 0) {{
                                                    console.log('图片加载成功:', img.src, img.naturalWidth, 'x', img.naturalHeight);
                                                }} else {{
                                                    console.log('图片加载失败:', img.src);
                                                    // 如果base64加载失败，尝试其他方法
                                                    if (img.src.startsWith('data:')) {{
                                                        console.log('base64图片加载失败，尝试重新加载');
                                                        img.src = img.src; // 重新设置src
                                                    }}
                                                }}
                                            }}, 100);
                                            
                                            return {{ success: true, width: width, height: height }};
                                        }}
                                        return {{ success: false, error: 'no parent node' }};
                                    }} catch (e) {{
                                        return {{ success: false, error: e.message }};
                                    }}
                                }}
                            """)
                            
                            # 如果替换成功，记录并继续处理下一个canvas
                            if result and result.get('success'):
                                logger.info(f"✅ 成功替换第 {i+1} 个容器的第 {j+1} 个canvas元素，尺寸: {result.get('width')}x{result.get('height')}")
                                modified_count += 1
                                
                                # 验证替换是否真的成功
                                try:
                                    await config.page.wait_for_timeout(500)  # 等待图片加载
                                    # 检查替换后的元素 - 使用JavaScript验证
                                    verify_result = await config.page.evaluate(f"""
                                        () => {{
                                            try {{
                                                const img = document.querySelector('img[src="{file_url}"]');
                                                if (img) {{
                                                    return {{
                                                        success: true,
                                                        src: img.src,
                                                        width: img.width || img.offsetWidth || img.naturalWidth,
                                                        height: img.height || img.offsetHeight || img.naturalHeight,
                                                        complete: img.complete,
                                                        naturalWidth: img.naturalWidth,
                                                        naturalHeight: img.naturalHeight
                                                    }};
                                                }} else {{
                                                    return {{ success: false, error: 'img element not found' }};
                                                }}
                                            }} catch (e) {{
                                                return {{ success: false, error: e.message }};
                                            }}
                                        }}
                                    """)
                                    
                                    if verify_result and verify_result.get('success'):
                                        logger.info(f"✅ 验证成功：第 {i+1} 个容器的第 {j+1} 个canvas替换成功")
                                    else:
                                        error_msg = verify_result.get('error', 'unknown error') if verify_result else 'no result'
                                        logger.warning(f"⚠️ 替换后未找到对应的img元素: {error_msg}")
                                except Exception as verify_e:
                                    logger.debug(f"验证替换结果时出错: {verify_e}")
                            else:
                                error_msg = result.get('error', 'unknown error') if result else 'no result'
                                logger.warning(f"替换第 {i+1} 个容器的第 {j+1} 个canvas失败: {error_msg}")
                                
                                # 如果上面的方法失败，尝试使用更直接的选择器
                                try:
                                    logger.info(f"尝试使用直接选择器替换第 {i+1} 个容器的第 {j+1} 个canvas...")
                                    direct_result = await config.page.evaluate(f"""
                                        () => {{
                                            try {{
                                                // 查找所有qr-item容器
                                                const qrContainers = document.querySelectorAll('.qr-item');
                                                if (qrContainers.length === 0) {{
                                                    return {{ success: false, error: 'no qr-item containers found' }};
                                                }}
                                                
                                                // 获取第 {i+1} 个容器内的canvas
                                                const container = qrContainers[{i}];
                                                if (!container) {{
                                                    return {{ success: false, error: 'container not found' }};
                                                }}
                                                
                                                const canvas = container.querySelector('canvas');
                                                if (!canvas) {{
                                                    return {{ success: false, error: 'canvas not found in container' }};
                                                }}
                                                
                                                // 获取尺寸并替换
                                                const width = canvas.width || canvas.offsetWidth || 60;
                                                const height = canvas.height || canvas.offsetHeight || 60;
                                                
                                                const img = document.createElement('img');
                                                img.src = '{file_url}';
                                                img.alt = '二维码';
                                                img.style.width = width + 'px';
                                                img.style.height = height + 'px';
                                                img.style.display = 'block';
                                                
                                                if (canvas.style.cssText) {{
                                                    img.style.cssText = canvas.style.cssText;
                                                }}
                                                
                                                canvas.parentNode.replaceChild(img, canvas);
                                                img.dispatchEvent(new Event('load', {{ bubbles: true }}));
                                                
                                                // 验证图片是否正确加载
                                                setTimeout(() => {{
                                                    if (img.complete && img.naturalWidth > 0) {{
                                                        console.log('备选方法图片加载成功:', img.src, img.naturalWidth, 'x', img.naturalHeight);
                                                    }} else {{
                                                        console.log('备选方法图片加载失败:', img.src);
                                                        // 如果base64加载失败，尝试其他方法
                                                        if (img.src.startsWith('data:')) {{
                                                            console.log('备选方法base64图片加载失败，尝试重新加载');
                                                            img.src = img.src; // 重新设置src
                                                        }}
                                                    }}
                                                }}, 100);
                                                
                                                return {{ success: true, width: width, height: height }};
                                            }} catch (e) {{
                                                return {{ success: false, error: e.message }};
                                            }}
                                        }}
                                    """)
                                    
                                    if direct_result and direct_result.get('success'):
                                        logger.info(f"✅ 使用直接选择器成功替换第 {i+1} 个容器的第 {j+1} 个canvas元素")
                                        modified_count += 1
                                        
                                        # 验证备选替换是否真的成功
                                        try:
                                            await config.page.wait_for_timeout(500)  # 等待图片加载
                                            # 检查替换后的元素 - 使用JavaScript验证
                                            verify_result = await config.page.evaluate(f"""
                                                () => {{
                                                    try {{
                                                        const img = document.querySelector('img[src="{file_url}"]');
                                                        if (img) {{
                                                            return {{
                                                                success: true,
                                                                src: img.src,
                                                                width: img.width || img.offsetWidth || img.naturalWidth,
                                                                height: img.height || img.offsetHeight || img.naturalHeight,
                                                                complete: img.complete,
                                                                naturalWidth: img.naturalWidth,
                                                                naturalHeight: img.naturalHeight
                                                            }};
                                                        }} else {{
                                                            return {{ success: false, error: 'img element not found' }};
                                                        }}
                                                    }} catch (e) {{
                                                        return {{ success: false, error: e.message }};
                                                    }}
                                                }}
                                            """)
                                            
                                            if verify_result and verify_result.get('success'):
                                                logger.info(f"✅ 备选方法验证成功：第 {i+1} 个容器的第 {j+1} 个canvas替换后的img元素")
                                            else:
                                                error_msg = verify_result.get('error', 'unknown error') if verify_result else 'no result'
                                                logger.warning(f"⚠️ 备选方法替换后未找到对应的img元素: {error_msg}")
                                        except Exception as verify_e:
                                            logger.debug(f"验证备选替换结果时出错: {verify_e}")
                                    else:
                                        direct_error = direct_result.get('error', 'unknown error') if direct_result else 'no result'
                                        logger.warning(f"直接选择器替换也失败: {direct_error}")
                                        
                                except Exception as direct_e:
                                    logger.error(f"直接选择器替换出错: {direct_e}")
                                
                        except Exception as canvas_e:
                            logger.error(f"替换第 {i+1} 个容器的第 {j+1} 个canvas时出错: {canvas_e}")
                                
                        except Exception as canvas_e:
                            logger.error(f"替换第 {j+1} 个canvas时出错: {canvas_e}")
                    
                    # 处理img元素 - 直接修改src
                    for j, img in enumerate(img_elements):
                        try:
                            # 先获取img元素信息
                            img_info = await config.page.evaluate("""
                                (img) => {
                                    if (!img) return null;
                                    
                                    return {
                                        originalSrc: img.src || '',
                                        originalAlt: img.alt || '',
                                        hasParent: img.parentNode ? true : false
                                    };
                                }
                            """, img)
                            
                            if not img_info:
                                logger.warning(f"无法获取第 {j+1} 个img元素信息，跳过")
                                continue
                            
                            # 使用JavaScript修改图片src并验证
                            result = await config.page.evaluate(f"""
                                (img) => {{
                                    if (!img) return {{ success: false, error: 'img element is null' }};
                                    
                                    try {{
                                        // 保存原始属性
                                        const originalSrc = '{img_info["originalSrc"]}';
                                        const originalAlt = '{img_info["originalAlt"]}';
                                        
                                        // 修改图片源
                                        img.src = '{file_url}';
                                        img.setAttribute('src', '{file_url}');
                                        
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
                                        
                                        // 返回修改结果
                                        return {{
                                            success: img.src === '{file_url}',
                                            originalSrc: originalSrc,
                                            newSrc: img.src
                                        }};
                                    }} catch (e) {{
                                        return {{ success: false, error: e.message }};
                                    }}
                                }}
                            """, img)
                            
                            # 验证修改是否成功
                            if result and result.get('success'):
                                modified_count += 1
                                logger.info(f"✅ 成功修改第 {j+1} 个img元素")
                            else:
                                error_msg = result.get('error', 'unknown error') if result else 'no result'
                                logger.warning(f"修改第 {j+1} 个img元素失败: {error_msg}")
                                
                                # 尝试强制修改
                                try:
                                    force_result = await config.page.evaluate(f"""
                                        (img) => {{
                                            if (!img) return false;
                                            
                                            try {{
                                                img.src = '{file_url}';
                                                img.setAttribute('src', '{file_url}');
                                                img.style.display = 'none';
                                                img.offsetHeight;
                                                img.style.display = '';
                                                return img.src === '{file_url}';
                                            }} catch (e) {{
                                                return false;
                                            }}
                                        }}
                                    """, img)
                                    
                                    if force_result:
                                        modified_count += 1
                                        logger.info(f"✅ 强制修改第 {j+1} 个img元素成功")
                                    else:
                                        logger.error(f"强制修改第 {j+1} 个img元素失败")
                                except Exception as force_e:
                                    logger.error(f"强制修改第 {j+1} 个img元素出错: {force_e}")
                            
                        except Exception as img_e:
                            logger.error(f"修改第 {j+1} 个img元素时出错: {img_e}")
                    
                    # 如果二维码容器内既没有canvas也没有img，尝试直接添加img
                    if len(canvas_elements) == 0 and len(img_elements) == 0:
                        try:
                            await config.page.evaluate(f"""
                                (element) => {{
                                    // 创建新的img元素
                                    const img = document.createElement('img');
                                    img.src = '{file_url}';
                                    img.alt = '二维码';
                                    img.style.width = '100px';
                                    img.style.height = '100px';
                                    img.style.display = 'block';
                                    
                                    // 添加到二维码容器元素
                                    element.appendChild(img);
                                    
                                    // 触发加载事件
                                    img.dispatchEvent(new Event('load', {{ bubbles: true }}));
                                }}
                            """, element)
                            
                            modified_count += 1
                            logger.info(f"✅ 成功添加新的img元素到第 {i+1} 个二维码容器")
                            
                        except Exception as add_e:
                            logger.error(f"添加img时出错: {add_e}")
                    
                except Exception as e:
                    logger.error(f"处理第 {i+1} 个二维码容器时出错: {e}")
            
            if modified_count > 0:
                logger.info(f"✅ 二维码修改成功，共修改 {modified_count} 个元素")
            else:
                logger.warning("⚠️ 未找到可修改的二维码元素")
            
            return modified_count > 0
            
        except Exception as e:
            logger.error(f"修改二维码时出错: {e}")
            return False
    


    
    async def run(self):
        """运行主流程"""
        logger.info(f"开始执行自动修改流程，VIN: {self.vin}, 新日期: {self.new_date}")
        
        try:
            report_url = await self.get_report_url()
            if not report_url:
                logger.error("无法获取报告链接，流程终止")
                return False, None
            
            logger.info(f"成功获取报告链接: {report_url}")
            
            success, screenshot_path = await self.modify_date_on_page(report_url)
            
            if success:
                logger.info("✅ 修改完成！")
                return True, screenshot_path
            else:
                logger.error("❌ 修改失败！")
                return False, screenshot_path
        except Exception as e:
            logger.error(f"执行流程时发生异常: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False, None

def run_async_task(task_id, vin, new_date, qr_code_url):
    """在后台运行异步任务"""
    try:
        # 更新任务状态为运行中
        redis_task_manager.update_task_status(task_id, 'running')
        logger.info(f"开始执行任务 {task_id}, VIN: {vin}, 日期: {new_date}")
        
        modifier = CarReportModifier(
            vin=vin,
            new_date=new_date,
            qr_code_url=qr_code_url,
            headless=True
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success, screenshot_path = loop.run_until_complete(modifier.run())
        
        logger.info(f"任务 {task_id} 执行完成，成功: {success}, 截图: {screenshot_path}")
        
        # 保存任务结果到Redis
        if success and screenshot_path:
            redis_task_manager.save_task_result(
                task_id=task_id,
                success=success,
                screenshot_path=screenshot_path
            )
        else:
            redis_task_manager.save_task_result(
                task_id=task_id,
                success=success,
                screenshot_path=screenshot_path if screenshot_path else None
            )
        
        loop.close()
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        # 保存失败结果到Redis
        redis_task_manager.save_task_result(
            task_id=task_id,
            success=False,
            error=str(e)
        )

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/query-report', methods=['POST'])
def query_report():
    """查询报告链接API"""
    try:
        data = request.get_json()
        vin = data.get('vin')
        
        if not vin:
            return jsonify({'error': 'VIN不能为空'}), 400
        
        # 创建CarReportModifier实例来获取报告链接
        modifier = CarReportModifier(vin=vin)
        
        # 在单独的事件循环中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report_url = loop.run_until_complete(modifier.get_report_url())
        finally:
            loop.close()
        
        if report_url:
            return jsonify({
                'report_url': report_url,
                'vin': vin,
                'message': '报告链接获取成功'
            })
        else:
            return jsonify({'error': '无法获取报告链接，请检查VIN码是否正确'}), 404
        
    except Exception as e:
        logger.error(f"查询报告链接API错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/modify', methods=['POST'])
def modify_report():
    """修改报告API"""
    try:
        # 检查Redis连接
        if not redis_task_manager.is_redis_connected():
            return jsonify({'error': 'Redis连接失败'}), 500
        
        data = request.get_json()
        vin = data.get('vin')
        new_date = data.get('date')
        qr_code_url = data.get('qr_code_url', "https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg")
        
        if not vin:
            return jsonify({'error': 'VIN不能为空'}), 400
        
        if not new_date:
            new_date = datetime.now().strftime("%Y-%m-%d")
        
        # 创建任务并获取任务ID
        task_id = redis_task_manager.create_task(vin, new_date, qr_code_url)
        
        # 在后台线程中运行任务
        thread = threading.Thread(
            target=run_async_task,
            args=(task_id, vin, new_date, qr_code_url)
        )
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'message': '任务已启动',
            'status': 'pending'
        })
        
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    try:
        # 检查Redis连接
        if not redis_task_manager.is_redis_connected():
            return jsonify({'error': 'Redis连接失败'}), 500
        
        task_info = redis_task_manager.get_task_info(task_id)
        if not task_info:
            return jsonify({'error': '任务不存在'}), 404
        
        # 合并所有信息
        result = {
            'task_id': task_id,
            **task_info.get('task_data', {}),
            **task_info.get('status_data', {}),
            **task_info.get('result_data', {})
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks')
def get_all_tasks():
    """获取所有任务"""
    try:
        # 检查Redis连接
        if not redis_task_manager.is_redis_connected():
            return jsonify({'error': 'Redis连接失败'}), 500
        
        tasks = redis_task_manager.get_all_tasks(limit=10)
        
        # 将任务列表转换为以任务ID为键的字典
        tasks_dict = {}
        for task in tasks:
            task_id = task.get('task_id')
            if task_id:
                tasks_dict[task_id] = task
        
        return jsonify(tasks_dict)
        
    except Exception as e:
        logger.error(f"获取所有任务失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    try:
        # 检查Redis连接
        if not redis_task_manager.is_redis_connected():
            return jsonify({'error': 'Redis连接失败'}), 500
        
        # 检查任务是否存在
        task_info = redis_task_manager.get_task_info(task_id)
        if not task_info:
            return jsonify({'error': '任务不存在'}), 404
        
        # 删除任务
        success = redis_task_manager.delete_task(task_id)
        if success:
            return jsonify({'message': '任务删除成功'})
        else:
            return jsonify({'error': '删除任务失败'}), 500
        
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs("static/screenshots", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    # 初始化Redis任务管理器
    redis_task_manager = init_redis_task_manager()
    
    # 检查Redis连接
    if not redis_task_manager.is_redis_connected():
        logger.warning("Redis连接失败，将使用内存存储（不推荐生产环境）")
    else:
        logger.info("Redis连接成功")
    
    app.run(debug=True, host='0.0.0.0', port=8090) 