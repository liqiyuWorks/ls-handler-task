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
import time
import signal
import sys
from playwright_config import PlaywrightConfig
from redis_task_manager import get_redis_task_manager, init_redis_task_manager

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(current_dir, 'templates'),
            static_folder=os.path.join(current_dir, 'static'))

# 初始化Redis任务管理器
redis_task_manager = None

# 进程监控和清理相关变量
process_monitor_thread = None
monitor_running = False

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
            # 先尝试APP接口获取报告链接
            logger.info(f"正在请求APP获取报告链接，VIN: {self.vin}")
            response = requests.get(self.base_url, params=self.params)
            response.raise_for_status()
            data = response.json()
            if data.get("Result") == 1 and data.get("Message") == "SUCCESS":
                report_url = data.get("ReturnObj")
                logger.info(f"APP接口成功获取报告链接: {report_url}")
                return report_url
            else:
                logger.warning(f"APP接口未成功: {data}")

            # 如果APP接口未获取到，再尝试API接口
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

            logger.error("未能通过APP或API接口获取报告链接")
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
        """修改页面中的二维码图片 - 专门针对'官方验证'、'专属保障'和'交易保障'三个二维码"""
        try:
            logger.info("🔄 开始替换页面中的二维码（官方验证 + 专属保障 + 交易保障）...")
            
            # 等待页面完全加载
            await config.page.wait_for_timeout(2000)
            
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
                    logger.info(f"✅ 成功将图片转换为base64编码，长度: {len(img_base64)} 字符")
            except Exception as e:
                logger.error(f"转换图片为base64失败: {e}")
                return False
            
            # 使用JavaScript直接查找并替换三个特定的二维码
            logger.info("🔍 使用JavaScript查找并替换'官方验证'、'专属保障'和'交易保障'二维码...")
            
            result = await config.page.evaluate(f"""
                () => {{
                    try {{
                        const targetTexts = ['官方验证', '专属保障', '交易保障'];
                        let modifiedCount = 0;
                        let results = [];
                        
                        // 查找所有qr-item容器
                        const qrContainers = document.querySelectorAll('.qr-item');
                        console.log('找到二维码容器数量:', qrContainers.length);
                        
                        if (qrContainers.length === 0) {{
                            return {{ 
                                success: false, 
                                error: '未找到.qr-item容器',
                                modifiedCount: 0 
                            }};
                        }}
                        
                        // 遍历每个容器
                        for (let i = 0; i < qrContainers.length; i++) {{
                            const container = qrContainers[i];
                            const spanElement = container.querySelector('span');
                            
                            if (!spanElement) {{
                                console.log('容器', i, '未找到span元素');
                                continue;
                            }}
                            
                            const containerText = spanElement.textContent.trim();
                            console.log('容器', i, '文本:', containerText);
                            
                            // 检查是否是目标容器
                            if (!targetTexts.includes(containerText)) {{
                                console.log('跳过非目标容器:', containerText);
                                continue;
                            }}
                            
                            console.log('处理目标容器:', containerText);
                            
                            // 查找canvas元素
                            const canvas = container.querySelector('canvas');
                            if (!canvas) {{
                                console.log('容器', containerText, '未找到canvas元素');
                                continue;
                            }}
                            
                            // 获取canvas尺寸
                            const width = canvas.width || canvas.offsetWidth || 60;
                            const height = canvas.height || canvas.offsetHeight || 60;
                            
                            // 创建新的img元素
                            const img = document.createElement('img');
                            img.src = '{file_url}';
                            img.alt = '二维码';
                            img.style.width = (width + 10) + 'px';
                            img.style.height = (height + 10) + 'px';
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
                                
                                modifiedCount++;
                                results.push({{
                                    containerText: containerText,
                                    width: width,
                                    height: height,
                                    success: true
                                }});
                                
                                console.log('成功替换容器:', containerText, '尺寸:', width, 'x', height);
                            }} else {{
                                console.log('canvas没有父节点，无法替换');
                                results.push({{
                                    containerText: containerText,
                                    success: false,
                                    error: 'canvas没有父节点'
                                }});
                            }}
                        }}
                        
                        return {{
                            success: true,
                            modifiedCount: modifiedCount,
                            results: results,
                            totalContainers: qrContainers.length
                        }};
                        
                    }} catch (e) {{
                        console.error('替换二维码时出错:', e);
                        return {{
                            success: false,
                            error: e.message,
                            modifiedCount: 0
                        }};
                    }}
                }}
            """)
            
            if result and result.get('success'):
                modified_count = result.get('modifiedCount', 0)
                total_containers = result.get('totalContainers', 0)
                results = result.get('results', [])
                
                logger.info(f"✅ 二维码替换完成！")
                logger.info(f"   总容器数: {total_containers}")
                logger.info(f"   成功替换: {modified_count} 个")
                
                # 显示详细结果
                for res in results:
                    if res.get('success'):
                        logger.info(f"   ✅ {res['containerText']}: {res['width']}x{res['height']}")
                    else:
                        logger.warning(f"   ⚠️ {res['containerText']}: {res.get('error', '未知错误')}")
                
                # 验证替换结果
                await self.verify_qr_replacement(config, file_url)
                
                return modified_count > 0
            else:
                error_msg = result.get('error', 'unknown error') if result else 'no result'
                logger.error(f"❌ 二维码替换失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"修改二维码时出错: {e}")
            return False
    
    async def verify_qr_replacement(self, config, file_url):
        """验证二维码替换结果"""
        try:
            logger.info("🔍 开始验证二维码替换结果...")
            
            # 等待图片加载
            await config.page.wait_for_timeout(1000)
            
            # 使用JavaScript验证替换结果
            verify_result = await config.page.evaluate(f"""
                () => {{
                    try {{
                        const targetTexts = ['官方验证', '专属保障'];
                        let verificationResults = [];
                        
                        // 查找所有qr-item容器
                        const qrContainers = document.querySelectorAll('.qr-item');
                        
                        for (let i = 0; i < qrContainers.length; i++) {{
                            const container = qrContainers[i];
                            const spanElement = container.querySelector('span');
                            
                            if (!spanElement) continue;
                            
                            const containerText = spanElement.textContent.trim();
                            
                            // 只检查目标容器
                            if (!targetTexts.includes(containerText)) continue;
                            
                            const img = container.querySelector('img');
                            const canvas = container.querySelector('canvas');
                            
                            if (img && !canvas) {{
                                // 成功替换：有img，没有canvas
                                verificationResults.push({{
                                    containerText: containerText,
                                    status: 'success',
                                    hasImg: true,
                                    hasCanvas: false,
                                    imgSrc: img.src,
                                    imgWidth: img.width || img.offsetWidth || img.naturalWidth,
                                    imgHeight: img.height || img.offsetHeight || img.naturalHeight
                                }});
                            }} else if (canvas && !img) {{
                                // 替换失败：有canvas，没有img
                                verificationResults.push({{
                                    containerText: containerText,
                                    status: 'failed',
                                    hasImg: false,
                                    hasCanvas: true,
                                    error: 'canvas未被替换'
                                }});
                            }} else if (img && canvas) {{
                                // 部分替换：既有img又有canvas
                                verificationResults.push({{
                                    containerText: containerText,
                                    status: 'partial',
                                    hasImg: true,
                                    hasCanvas: true,
                                    warning: 'canvas和img同时存在'
                                }});
                            }} else {{
                                // 异常状态：既没有img也没有canvas
                                verificationResults.push({{
                                    containerText: containerText,
                                    status: 'error',
                                    hasImg: false,
                                    hasCanvas: false,
                                    error: '既没有canvas也没有img'
                                }});
                            }}
                        }}
                        
                        return {{
                            success: true,
                            results: verificationResults,
                            totalChecked: verificationResults.length
                        }};
                        
                    }} catch (e) {{
                        return {{
                            success: false,
                            error: e.message
                        }};
                    }}
                }}
            """)
            
            if verify_result and verify_result.get('success'):
                results = verify_result.get('results', [])
                total_checked = verify_result.get('totalChecked', 0)
                
                logger.info(f"🔍 验证完成，检查了 {total_checked} 个目标容器")
                
                success_count = 0
                for res in results:
                    if res['status'] == 'success':
                        logger.info(f"   ✅ {res['containerText']}: 替换成功 ({res['imgWidth']}x{res['imgHeight']})")
                        success_count += 1
                    elif res['status'] == 'failed':
                        logger.warning(f"   ❌ {res['containerText']}: {res['error']}")
                    elif res['status'] == 'partial':
                        logger.warning(f"   ⚠️ {res['containerText']}: {res['warning']}")
                    elif res['status'] == 'error':
                        logger.error(f"   💥 {res['containerText']}: {res['error']}")
                
                logger.info(f"🔍 验证结果: {success_count}/{total_checked} 个容器替换成功")
                return success_count == total_checked
            else:
                error_msg = verify_result.get('error', 'unknown error') if verify_result else 'no result'
                logger.error(f"❌ 验证失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"验证二维码替换结果时出错: {e}")
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

def process_monitor():
    """进程监控和自动清理函数"""
    global monitor_running
    logger.info("🔍 启动进程监控线程...")
    
    while monitor_running:
        try:
            # 检查Chrome进程数量
            chrome_count = PlaywrightConfig.get_system_chrome_process_count()
            
            if chrome_count > 10:  # 如果Chrome进程超过10个，进行清理
                logger.warning(f"⚠️ 检测到过多Chrome进程 ({chrome_count}个)，开始清理...")
                asyncio.run(PlaywrightConfig.cleanup_all_chrome_processes())
            
            # 每30秒检查一次
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"进程监控出错: {e}")
            time.sleep(60)  # 出错时等待更长时间

def start_process_monitor():
    """启动进程监控"""
    global process_monitor_thread, monitor_running
    
    if process_monitor_thread is None or not process_monitor_thread.is_alive():
        monitor_running = True
        process_monitor_thread = threading.Thread(target=process_monitor, daemon=True)
        process_monitor_thread.start()
        logger.info("✅ 进程监控已启动")

def stop_process_monitor():
    """停止进程监控"""
    global monitor_running
    monitor_running = False
    logger.info("🛑 进程监控已停止")

def signal_handler(signum, frame):
    """信号处理器，确保程序退出时清理资源"""
    logger.info(f"📡 收到信号 {signum}，开始清理资源...")
    
    # 停止进程监控
    stop_process_monitor()
    
    # 清理所有Chrome进程
    try:
        asyncio.run(PlaywrightConfig.cleanup_all_chrome_processes())
    except Exception as e:
        logger.error(f"清理Chrome进程时出错: {e}")
    
    logger.info("✅ 资源清理完成，程序退出")
    sys.exit(0)

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
        
        try:
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
        finally:
            # 🚀 新增：任务完成后强制清理Chrome进程
            try:
                logger.info(f"🧹 任务 {task_id} 完成，开始清理Chrome进程...")
                loop.run_until_complete(PlaywrightConfig.cleanup_all_chrome_processes())
                logger.info(f"✅ 任务 {task_id} Chrome进程清理完成")
            except Exception as cleanup_error:
                logger.error(f"清理Chrome进程时出错: {cleanup_error}")
            
            # 关闭事件循环
            loop.close()
            
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        
        # 🚀 新增：即使任务失败也要清理Chrome进程
        try:
            logger.info(f"🧹 任务 {task_id} 失败，开始清理Chrome进程...")
            asyncio.run(PlaywrightConfig.cleanup_all_chrome_processes())
            logger.info(f"✅ 任务 {task_id} Chrome进程清理完成")
        except Exception as cleanup_error:
            logger.error(f"清理Chrome进程时出错: {cleanup_error}")
        
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

@app.route('/api/tasks/clear-all', methods=['DELETE'])
def clear_all_tasks():
    """清空所有任务记录"""
    try:
        # 检查Redis连接
        if not redis_task_manager.is_redis_connected():
            return jsonify({'error': 'Redis连接失败'}), 500
        
        # 清空所有任务
        success = redis_task_manager.clear_all_tasks()
        if success:
            return jsonify({'message': '所有任务记录已清空'})
        else:
            return jsonify({'error': '清空任务记录失败'}), 500
        
    except Exception as e:
        logger.error(f"清空所有任务失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/process-status')
def get_process_status():
    """获取系统进程状态"""
    try:
        chrome_count = PlaywrightConfig.get_system_chrome_process_count()
        chrome_processes = PlaywrightConfig().get_chrome_processes()
        
        return jsonify({
            'chrome_process_count': chrome_count,
            'chrome_processes': chrome_processes,
            'monitor_running': monitor_running,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取进程状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/cleanup-chrome', methods=['POST'])
def cleanup_chrome_processes():
    """手动清理Chrome进程"""
    try:
        logger.info("🧹 收到手动清理Chrome进程请求")
        asyncio.run(PlaywrightConfig.cleanup_all_chrome_processes())
        
        # 获取清理后的状态
        chrome_count = PlaywrightConfig.get_system_chrome_process_count()
        
        return jsonify({
            'message': 'Chrome进程清理完成',
            'remaining_chrome_count': chrome_count,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"手动清理Chrome进程失败: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs("static/screenshots", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 初始化Redis任务管理器
    redis_task_manager = init_redis_task_manager()
    
    # 检查Redis连接
    if not redis_task_manager.is_redis_connected():
        logger.warning("Redis连接失败，将使用内存存储（不推荐生产环境）")
    else:
        logger.info("Redis连接成功")
    
    # 启动进程监控
    start_process_monitor()
    
    # 启动时清理可能存在的僵尸Chrome进程
    try:
        logger.info("🧹 启动时清理现有Chrome进程...")
        asyncio.run(PlaywrightConfig.cleanup_all_chrome_processes())
        logger.info("✅ 启动时Chrome进程清理完成")
    except Exception as e:
        logger.warning(f"启动时清理Chrome进程失败: {e}")
    
    logger.info("🚀 车辆报告修改Web服务启动中...")
    logger.info("📊 进程监控已启用，将自动清理Chrome僵尸进程")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8090)
    except KeyboardInterrupt:
        logger.info("📡 收到键盘中断信号")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        signal_handler(signal.SIGTERM, None) 