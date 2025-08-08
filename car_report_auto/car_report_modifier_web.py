#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆报告修改Web界面 - Docker 优化版本
"""

from flask import Flask, render_template, request, jsonify
import asyncio
import json
import requests
from datetime import datetime
from playwright.async_api import async_playwright
from loguru import logger
import threading
import queue
import os
import tempfile
import shutil
from playwright_config import PlaywrightConfig

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(current_dir, 'templates'),
            static_folder=os.path.join(current_dir, 'static'))

# 全局任务队列
task_queue = queue.Queue()
results = {}

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
    
    async def modify_date_on_page(self, url):
        """在页面上修改日期数据 - Docker 优化版本"""
        try:
            async with PlaywrightConfig(headless=self.headless) as config:
                # 导航到页面
                if not await config.navigate_to_page(url):
                    return False, await config.take_screenshot("page_load_error")
                
                # 尝试多种定位方式
                selectors = [
                    "xpath=/html/body/div[1]/div[1]/div[1]/div[5]/span[1]",
                    "//span[contains(@class, 'date')]",
                    "//div[contains(@class, 'date')]//span",
                    "//span[contains(text(), '-')]",
                    "//div[contains(@class, 'date')]",
                    "//span[contains(@class, 'time')]",
                    "//div[contains(@class, 'time')]//span",
                    "//*[contains(text(), '-') and contains(text(), '202')]",
                    "//*[contains(text(), '报告发布日期')]",
                    "//*[contains(text(), '发布日期')]",
                    "//*[contains(text(), '日期')]",
                    "//span[contains(text(), '202')]",
                    "//div[contains(text(), '202')]",
                    "//*[contains(text(), '2024')]",
                    "//*[contains(text(), '2023')]",
                    "//*[contains(text(), '2022')]",
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
                    return False, await config.take_screenshot("date_modification_failed")
                
                # 等待页面稳定
                await config.page.wait_for_timeout(2000)
                
                # 保存修改后的页面截图
                screenshot_path = await config.take_screenshot("modified_report")
                
                return True, screenshot_path
                
        except Exception as e:
            logger.error(f"修改日期时出错: {e}")
            return False, None
                
                # 尝试多种定位方式
                selectors = [
                    "xpath=/html/body/div[1]/div[1]/div[1]/div[5]/span[1]",
                    "//span[contains(@class, 'date')]",
                    "//div[contains(@class, 'date')]//span",
                    "//span[contains(text(), '-')]",
                    "//div[contains(@class, 'date')]",
                    "//span[contains(@class, 'time')]",
                    "//div[contains(@class, 'time')]//span",
                    "//*[contains(text(), '-') and contains(text(), '202')]",
                    "//*[contains(text(), '报告发布日期')]",
                    "//*[contains(text(), '发布日期')]",
                    "//*[contains(text(), '日期')]",
                    "//span[contains(text(), '202')]",
                    "//div[contains(text(), '202')]",
                    "//*[contains(text(), '2024')]",
                    "//*[contains(text(), '2023')]",
                    "//*[contains(text(), '2022')]",
                ]
                
                element = None
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            logger.info(f"找到日期元素，使用选择器: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"选择器 {selector} 失败: {e}")
                        continue
                
                if not element:
                    logger.error("未找到指定的日期元素")
                    return False, await self._take_screenshot(page, "no_date_element")
                
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
                modification_success = False
                try:
                    # 使用更安全的 JavaScript 执行方式
                    await page.evaluate(f"""
                        (element) => {{
                            try {{
                                // 保存原始内容
                                const originalContent = element.textContent;
                                
                                // 更新文本内容
                                element.textContent = '{full_text}';
                                element.innerText = '{full_text}';
                                
                                // 如果是输入框，也更新值
                                if (element.tagName === 'INPUT') {{
                                    element.value = '{self.new_date}';
                                }}
                                
                                // 触发事件
                                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                element.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                
                                // 强制重绘
                                element.style.transform = 'translateZ(0)';
                                
                                console.log('日期修改成功:', '{full_text}');
                                return true;
                            }} catch (error) {{
                                console.error('日期修改失败:', error);
                                return false;
                            }}
                        }}
                    """, element)
                    
                    # 验证修改是否成功
                    await page.wait_for_timeout(1000)
                    new_content = await element.text_content()
                    if self.new_date in new_content:
                        modification_success = True
                        logger.info(f"日期修改成功: {new_content}")
                    else:
                        logger.warning(f"日期修改可能失败，当前内容: {new_content}")
                        
                except Exception as e:
                    logger.error(f"修改日期失败: {e}")
                
                if not modification_success:
                    return False, await self._take_screenshot(page, "date_modification_failed")
                
                # 等待页面稳定
                await page.wait_for_timeout(2000)
                
                # 保存修改后的页面截图
                screenshot_path = await self._take_screenshot(page, "modified_report")
                
                return True, screenshot_path
                
        except Exception as e:
            logger.error(f"修改日期时出错: {e}")
            if page:
                return False, await self._take_screenshot(page, "error")
            return False, None
        finally:
            # 确保资源清理
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
            if browser:
                try:
                    await browser.close()
                except:
                    pass
    

    
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

def run_async_task(task_id, vin, new_date, qr_code_url):
    """在后台运行异步任务"""
    try:
        modifier = CarReportModifier(
            vin=vin,
            new_date=new_date,
            qr_code_url=qr_code_url,
            headless=True
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success, screenshot_path = loop.run_until_complete(modifier.run())
        
        # 保留VIN和日期信息
        results[task_id] = {
            'success': success,
            'screenshot_path': screenshot_path,
            'status': 'completed',
            'vin': vin,
            'new_date': new_date
        }
        
        loop.close()
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        results[task_id] = {
            'success': False,
            'error': str(e),
            'status': 'failed',
            'vin': vin,
            'new_date': new_date
        }

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/modify', methods=['POST'])
def modify_report():
    """修改报告API"""
    try:
        data = request.get_json()
        vin = data.get('vin')
        new_date = data.get('date')
        qr_code_url = data.get('qr_code_url', "https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg")
        
        if not vin:
            return jsonify({'error': 'VIN不能为空'}), 400
        
        if not new_date:
            new_date = datetime.now().strftime("%Y-%m-%d")
        
        # 生成任务ID
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 初始化任务状态
        results[task_id] = {
            'status': 'running',
            'vin': vin,
            'new_date': new_date
        }
        
        # 在后台线程中运行任务
        thread = threading.Thread(
            target=run_async_task,
            args=(task_id, vin, new_date, qr_code_url)
        )
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'message': '任务已启动',
            'status': 'running'
        })
        
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    if task_id not in results:
        return jsonify({'error': '任务不存在'}), 404
    
    result = results[task_id]
    return jsonify(result)

@app.route('/api/tasks')
def get_all_tasks():
    """获取所有任务"""
    return jsonify(results)

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs("static/screenshots", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=8090) 