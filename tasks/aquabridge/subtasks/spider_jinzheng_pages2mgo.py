#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AquaBridge 多页面数据管道 - 优化版本
支持 ffa_price_signals 和 p4tc_spot_decision 两个页面的数据抓取、处理和存储
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加当前目录到Python路径，以便导入本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from pkg.public.models import BaseModel
from pkg.public.decorator import decorate

# 导入本地模块
from enhanced_formatter import EnhancedFormatter
from mongodb_storage import MongoDBStorage, load_config
from session_manager import SessionManager


class SpiderJinzhengPages2mgo(BaseModel):
    """AquaBridge 数据管道主类 - 优化版本"""
    
    def __init__(self):
        # 初始化配置
        config = {}
        super(SpiderJinzhengPages2mgo, self).__init__(config)
        
        # 加载MongoDB配置
        config_file = os.path.join(parent_dir, "mongodb_config.json")
        self.config = load_config(config_file)
        self.mongodb_enabled = self.config.get('enabled', False)
        self.storage = None
        
        # 支持的页面配置
        self.supported_pages = {
            "ffa_price_signals": {
                "name": "FFA价格信号",
                "description": "单边价格信号汇总下的FFA数据",
                "formatter": EnhancedFormatter()
            },
            "p4tc_spot_decision": {
                "name": "P4TC现货应用决策", 
                "description": "P4TC现货策略的应用决策数据",
                "formatter": EnhancedFormatter()
            }
        }

    def _init_mongodb(self, page_key: str):
        """初始化MongoDB连接"""
        if self.mongodb_enabled:
            try:
                self.storage = MongoDBStorage(self.config, page_key)
            except (ConnectionError, ImportError, ValueError):
                self.mongodb_enabled = False
    
    def _close_mongodb(self):
        """关闭MongoDB连接"""
        if self.storage:
            self.storage.close()
            self.storage = None
    
    def _process_data(self, page_key: str, raw_data: List[Dict], save_file: bool, store_mongodb: bool) -> bool:
        """处理数据的公共方法"""
        if not raw_data:
            return False
        
        # 格式化数据
        formatted_data = self.format_data(page_key, raw_data)
        if not formatted_data:
            return False
        
        # 保存到文件
        if save_file:
            self.save_to_file(page_key, formatted_data)
        
        # 存储到MongoDB
        if store_mongodb:
            self.store_data(page_key, formatted_data)
        
        return True
    
    def format_data(self, page_key: str, raw_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """格式化数据"""
        if page_key not in self.supported_pages:
            return None
        
        try:
            # 构造原始数据格式
            raw_data_dict = {
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "browser": "chromium",
                "page_name": self.supported_pages[page_key]['name'],
                "tables": raw_data
            }
            
            # 使用增强型格式化器
            formatter = self.supported_pages[page_key]['formatter']
            formatted_data = formatter.format_data(raw_data_dict)
            
            return formatted_data if formatted_data and formatted_data.get('contracts') else None
                
        except (ValueError, KeyError, TypeError):
            return None
    
    def store_data(self, page_key: str, data: Dict[str, Any]) -> bool:
        """存储数据到MongoDB"""
        if not self.mongodb_enabled:
            return True
        
        try:
            self._init_mongodb(page_key)
            
            if not self.storage:
                return False
            
            # 添加页面标识到metadata
            if 'metadata' in data:
                data['metadata']['page_key'] = page_key
            else:
                data['page_key'] = page_key
                data['page_name'] = self.supported_pages[page_key]['name']
            
            return self.storage.store_ffa_data(data)
            
        except (ConnectionError, ValueError, KeyError):
            return False
    
    def save_to_file(self, page_key: str, data: Dict[str, Any], output_dir: str = "output") -> str:
        """保存数据到文件"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{page_key}_data_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def process_page(self, page_key: str, browser: str = "firefox", headless: bool = False, 
                    save_file: bool = True, store_mongodb: bool = True) -> bool:
        """处理单个页面的完整流程"""
        try:
            # 使用SessionManager处理页面
            with SessionManager(browser_type=browser, headless=headless) as session:
                # 登录
                if not session.login_once():
                    return False
                
                # 抓取数据
                raw_data = session.scrape_page(page_key)
                return self._process_data(page_key, raw_data, save_file, store_mongodb)
        except (ConnectionError, ValueError, KeyError, TimeoutError):
            return False
    
    def process_all_pages(self, browser: str = "firefox", headless: bool = False,
                         save_file: bool = True, store_mongodb: bool = True) -> Dict[str, bool]:
        """处理所有支持的页面（优化版本，复用登录会话）"""
        results = {}
        page_keys = list(self.supported_pages.keys())
        
        for page_key in page_keys:
            try:
                # 为每个页面创建独立的会话
                with SessionManager(browser_type=browser, headless=headless) as session:
                    # 登录
                    if not session.login_once():
                        results[page_key] = False
                        continue
                    
                    # 抓取数据
                    raw_data = session.scrape_page(page_key)
                    results[page_key] = self._process_data(page_key, raw_data, save_file, store_mongodb)
                        
            except (ConnectionError, ValueError, KeyError, TimeoutError):
                results[page_key] = False
        
        return results
    

    @decorate.exception_capture_close_datebase
    def run(self, task=None):
        """主运行方法 - 兼容原有接口"""
        if task is None:
            task = {}
        # 从task参数中获取配置
        page_key = task.get('page_key', 'all')  # 默认处理所有页面
        browser = task.get('browser', 'chromium')
        headless = task.get('headless', True)
        save_file = task.get('save_file', True)
        store_mongodb = task.get('store_mongodb', True)
        
        try:
            if page_key == 'all':
                # 处理所有页面
                results = self.process_all_pages(
                    browser=browser,
                    headless=headless,
                    save_file=save_file,
                    store_mongodb=store_mongodb
                )
                
                # 返回处理结果
                success_count = sum(1 for success in results.values() if success)
                total_count = len(results)
                
                return {
                    'status': 'success' if success_count > 0 else 'failed',
                    'results': results,
                    'success_count': success_count,
                    'total_count': total_count
                }
                
            elif page_key in self.supported_pages:
                # 处理指定页面
                success = self.process_page(
                    page_key=page_key,
                    browser=browser,
                    headless=headless,
                    save_file=save_file,
                    store_mongodb=store_mongodb
                )
                
                return {
                    'status': 'success' if success else 'failed',
                    'page_key': page_key,
                    'success': success
                }
            else:
                return {
                    'status': 'failed',
                    'error': f'不支持的页面: {page_key}'
                }
                
        except (ConnectionError, ValueError, KeyError, TimeoutError) as e:
            return {
                'status': 'failed',
                'error': str(e)
            }
        finally:
            # 清理资源
            self._close_mongodb()
