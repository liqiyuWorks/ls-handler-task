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
                    return False, await config.save_element_as_image('//*[@id="reportRef"]', "date_modification_failed")
                
                # 等待页面稳定
                await config.page.wait_for_timeout(3000)  # 增加等待时间确保页面完全渲染
                
                # 查找并点击所有"展开详情"按钮
                await self.expand_all_details(config)
                
                # 等待展开操作完成后页面重新渲染
                await config.page.wait_for_timeout(2000)
                
                # 确保所有资源都已加载完成
                await config.page.wait_for_load_state('networkidle')
                
                # 确保页面内容完全加载，并准备整页捕获
                logger.info("🔄 准备进行整页捕获，类似getfireshot.com的处理方式...")
                await self.ensure_full_content_loaded(config)
                
                # 📸 截取reportRef元素部分
                # ✨ 特点：
                # 1. 等待所有区域加载完毕
                # 2. 自动滚动回到页面顶部
                # 3. 只捕获reportRef元素
                # 4. 高质量PNG输出
                logger.info("📸 开始截取reportRef元素...")
                screenshot_path = await config.save_element_as_image('//*[@id="reportRef"]', "modified_report")
                
                return True, screenshot_path
                
        except Exception as e:
            logger.error(f"修改日期时出错: {e}")
            return False, None
    
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
    
    async def ensure_full_content_loaded(self, config):
        """确保完整内容已加载和渲染"""
        try:
            logger.info("确保报告内容完全加载...")
            
            # 等待网络空闲
            await config.page.wait_for_load_state('networkidle')
            
            # 滚动到reportRef元素顶部
            try:
                report_element = await config.page.query_selector('//*[@id="reportRef"]')
                if report_element:
                    await report_element.scroll_into_view_if_needed()
                    await config.page.wait_for_timeout(1000)
            except:
                pass
            
            # 检查并等待特定内容区域加载
            content_selectors = [
                '//*[@id="reportRef"]/div[2]/div/div[1]/div/div/div',
                '//*[@id="reportRef"]//div[contains(@class, "content")]',
                '//*[@id="reportRef"]//div[contains(@class, "detail")]',
                '//*[@id="reportRef"]//div[contains(@class, "report")]',
                '//*[@id="reportRef"]//img',  # 确保图片加载
                '//*[@id="reportRef"]//canvas',  # 确保图表加载
            ]
            
            for selector in content_selectors:
                try:
                    elements = await config.page.locator(selector).all()
                    if elements:
                        logger.info(f"等待 {len(elements)} 个元素加载完成: {selector}")
                        # 等待每个元素都可见
                        for element in elements:
                            try:
                                await element.wait_for(state='visible', timeout=2000)
                            except:
                                continue
                except:
                    continue
            
            # 强制等待所有图片加载完成
            try:
                await config.page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            const images = document.querySelectorAll('#reportRef img');
                            let loadedCount = 0;
                            const totalImages = images.length;
                            
                            if (totalImages === 0) {
                                resolve();
                                return;
                            }
                            
                            images.forEach(img => {
                                if (img.complete) {
                                    loadedCount++;
                                } else {
                                    img.onload = () => {
                                        loadedCount++;
                                        if (loadedCount === totalImages) {
                                            resolve();
                                        }
                                    };
                                    img.onerror = () => {
                                        loadedCount++;
                                        if (loadedCount === totalImages) {
                                            resolve();
                                        }
                                    };
                                }
                            });
                            
                            if (loadedCount === totalImages) {
                                resolve();
                            }
                            
                            // 5秒超时
                            setTimeout(resolve, 5000);
                        });
                    }
                """)
                logger.info("所有图片加载完成")
            except Exception as e:
                logger.warning(f"等待图片加载时出错: {e}")
            
            # 最终等待确保渲染完成
            await config.page.wait_for_timeout(2000)
            
            # 关键步骤：滚动回到页面顶部，准备整页截图
            logger.info("滚动到页面顶部，准备整页捕获...")
            await config.page.evaluate("window.scrollTo(0, 0)")
            await config.page.wait_for_timeout(1000)  # 等待滚动完成
            
            # 确认滚动位置
            scroll_position = await config.page.evaluate("window.pageYOffset")
            logger.info(f"当前页面滚动位置: {scroll_position}px")
            
            logger.info("内容加载验证完成，已准备好整页捕获")
            
        except Exception as e:
            logger.error(f"确保内容加载时出错: {e}")

    
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
        
        tasks = redis_task_manager.get_all_tasks(limit=100)
        
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