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
import threading

# 添加当前目录到Python路径，以便导入本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from pkg.public.models import BaseModel
from pkg.public.decorator import decorate

# 导入本地模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.enhanced_formatter import EnhancedFormatter
from modules.mongodb_storage import MongoDBStorage, load_config
from modules.session_manager import SessionManager


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
        
        # 性能优化配置
        self.timeout_config = {
            'page_timeout': 6000,      # 页面超时 6秒
            'navigation_timeout': 8000, # 导航超时 8秒
            'element_timeout': 3000,    # 元素等待超时 3秒
            'login_timeout': 6000       # 登录超时 6秒
        }
        
        # 快速模式配置
        self.fast_mode_config = {
            'page_timeout': 4000,      # 快速模式页面超时 4秒
            'navigation_timeout': 6000, # 快速模式导航超时 6秒
            'element_timeout': 2000,    # 快速模式元素等待超时 2秒
            'login_timeout': 4000       # 快速模式登录超时 4秒
        }
        
        # 缓存机制
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.cache_ttl = 300  # 缓存5分钟
        
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
            },
            "european_line_signals": {
                "name": "欧线价格信号",
                "description": "单边价格信号汇总下的欧线数据",
                "formatter": EnhancedFormatter()
            },
            "trading_opportunity_42d": {
                "name": "交易机会汇总（42天后）",
                "description": "单边价格信号汇总下的交易机会汇总（42天后）数据",
                "formatter": EnhancedFormatter(),
                "is_screenshot": True  # 标记为截图类型页面
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
    
    def _get_cache_key(self, page_key: str) -> str:
        """生成缓存键"""
        return f"{page_key}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    def _get_cached_data(self, page_key: str) -> Optional[Dict]:
        """获取缓存数据"""
        with self.cache_lock:
            cache_key = self._get_cache_key(page_key)
            if cache_key in self.cache:
                data, timestamp = self.cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_ttl:
                    return data
                else:
                    del self.cache[cache_key]
        return None
    
    def _set_cached_data(self, page_key: str, data: Dict):
        """设置缓存数据"""
        with self.cache_lock:
            cache_key = self._get_cache_key(page_key)
            self.cache[cache_key] = (data, datetime.now().timestamp())
    
    
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
            # 检查是否为截图类型页面
            is_screenshot = self.supported_pages[page_key].get("is_screenshot", False)
            
            if is_screenshot:
                # 截图类型数据：直接使用原始数据格式
                if raw_data and len(raw_data) > 0 and raw_data[0].get("data_type") == "screenshot":
                    screenshot_data = raw_data[0]
                    formatted_data = {
                        "metadata": {
                            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                            "browser": "chromium",
                            "page_name": self.supported_pages[page_key]['name'],
                            "data_source": "AquaBridge",
                            "version": "1.0",
                            "swap_date": screenshot_data.get("metadata", {}).get("swap_date", datetime.now().strftime("%Y-%m-%d")),
                            "page_title": screenshot_data.get("metadata", {}).get("page_title", "42天后单边交易机会汇总")
                        },
                        "screenshot": {
                            "path": screenshot_data.get("screenshot_path", ""),
                            "data_type": "screenshot"
                        }
                    }
                    return formatted_data
                else:
                    return None
            else:
                # 普通数据格式：使用增强型格式化器
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
                
        except (ValueError, KeyError, TypeError) as e:
            print(f"格式化数据失败: {e}")
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
                         save_file: bool = True, store_mongodb: bool = True, 
                         parallel: bool = True, max_workers: int = 2, 
                         fast_mode: bool = False) -> Dict[str, bool]:
        """处理所有支持的页面（优化版本，避免多线程Playwright问题）"""
        results = {}
        page_keys = list(self.supported_pages.keys())
        
        if parallel and len(page_keys) > 1:
            # 使用进程池而不是线程池来避免Playwright线程安全问题
            try:
                from multiprocessing import Pool
                
                # 创建处理函数
                def process_single_page_wrapper(args):
                    page_key, browser, headless, save_file, store_mongodb, _ = args
                    try:
                        with SessionManager(browser_type=browser, headless=headless) as session:
                            if not session.login_once():
                                return page_key, False
                            
                            raw_data = session.scrape_page(page_key)
                            success = self._process_data(page_key, raw_data, save_file, store_mongodb)
                            return page_key, success
                    except (ConnectionError, ValueError, KeyError, TimeoutError, ImportError):
                        return page_key, False
                
                # 准备参数
                args_list = [
                    (page_key, browser, headless, save_file, store_mongodb, fast_mode)
                    for page_key in page_keys
                ]
                
                # 使用进程池处理
                with Pool(processes=min(max_workers, len(page_keys))) as pool:
                    results_list = pool.map(process_single_page_wrapper, args_list)
                
                # 转换结果格式
                results = {page_key: success for page_key, success in results_list}
                
            except (ImportError, OSError, RuntimeError):
                # 如果multiprocessing不可用或失败，回退到串行处理
                results = self._process_pages_serially(page_keys, browser, headless, save_file, store_mongodb, fast_mode)
        else:
            # 串行处理
            results = self._process_pages_serially(page_keys, browser, headless, save_file, store_mongodb, fast_mode)
        
        return results
    
    def _process_pages_serially(self, page_keys: List[str], browser: str, headless: bool, 
                               save_file: bool, store_mongodb: bool, fast_mode: bool) -> Dict[str, bool]:
        """串行处理页面"""
        results = {}
        for page_key in page_keys:
            try:
                with SessionManager(browser_type=browser, headless=headless) as session:
                    if not session.login_once():
                        results[page_key] = False
                        continue
                    
                    raw_data = session.scrape_page(page_key)
                    results[page_key] = self._process_data(page_key, raw_data, save_file, store_mongodb)
            except (ConnectionError, ValueError, KeyError, TimeoutError):
                results[page_key] = False
        return results
    
    def process_all_pages_stable(self, browser: str = "firefox", headless: bool = False,
                                save_file: bool = True, store_mongodb: bool = True, 
                                fast_mode: bool = False) -> Dict[str, bool]:
        """稳定的页面处理方法（串行处理，避免多线程问题）"""
        return self._process_pages_serially(
            list(self.supported_pages.keys()), 
            browser, headless, save_file, store_mongodb, fast_mode
        )
    
    def quick_run(self, page_key: str = 'all', browser: str = 'chromium') -> Dict[str, Any]:
        """快速运行方法 - 使用最优配置"""
        task = {
            'page_key': page_key,
            'browser': browser,
            'headless': True,
            'save_file': True,
            'store_mongodb': True,
            'parallel': True,
            'max_workers': 2,
            'fast_mode': True
        }
        return self.run(task)
    
    def get_performance_stats(self, results: Dict[str, bool]) -> Dict[str, Any]:
        """获取性能统计信息"""
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'success_count': success_count,
            'total_count': total_count,
            'success_rate': round(success_rate, 1),
            'failed_pages': [k for k, v in results.items() if not v]
        }

    @decorate.exception_capture_close_datebase
    def run(self, task=None):
        """主运行方法 - 兼容原有接口"""
        if task is None:
            task = {}
        
        # 辅助函数：从环境变量或task参数获取配置，支持布尔值转换
        def get_config(key: str, default_value: Any, env_key: str = None) -> Any:
            """从环境变量或task参数获取配置值"""
            if env_key is None:
                env_key = f"SPIDER_{key.upper()}"
            
            # 优先从环境变量读取
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 处理布尔值
                if isinstance(default_value, bool):
                    return env_value.lower() in ('true', '1', 'yes', 'on')
                # 处理整数
                elif isinstance(default_value, int):
                    try:
                        return int(env_value)
                    except ValueError:
                        return default_value
                # 处理字符串
                else:
                    return env_value
            
            # 其次从task参数读取
            if key in task:
                return task[key]
            
            # 最后使用默认值
            return default_value
        
        # 从环境变量或task参数中获取配置
        page_key = get_config('page_key', 'trading_opportunity_42d', 'SPIDER_PAGE_KEY')
        browser = get_config('browser', 'firefox', 'SPIDER_BROWSER')
        headless = get_config('headless', False, 'SPIDER_HEADLESS')
        save_file = get_config('save_file', True, 'SPIDER_SAVE_FILE')
        store_mongodb = get_config('store_mongodb', True, 'SPIDER_STORE_MONGODB')
        parallel = get_config('parallel', False, 'SPIDER_PARALLEL')
        max_workers = get_config('max_workers', 2, 'SPIDER_MAX_WORKERS')
        fast_mode = get_config('fast_mode', False, 'SPIDER_FAST_MODE')
        stable_mode = get_config('stable_mode', True, 'SPIDER_STABLE_MODE')
        
        try:
            if page_key == 'all':
                # 处理所有页面
                if stable_mode:
                    # 使用稳定模式（一次登录，串行处理）
                    results = self.process_all_pages_stable(
                        browser=browser,
                        headless=headless,
                        save_file=save_file,
                        store_mongodb=store_mongodb,
                        fast_mode=fast_mode
                    )
                else:
                    # 使用并行模式（一次登录，多标签页并行处理）
                    results = self.process_all_pages(
                        browser=browser,
                        headless=headless,
                        save_file=save_file,
                        store_mongodb=store_mongodb,
                        parallel=parallel,
                        max_workers=max_workers,
                        fast_mode=fast_mode
                    )
                
                # 返回处理结果
                stats = self.get_performance_stats(results)
                
                return {
                    'status': 'success' if stats['success_count'] > 0 else 'failed',
                    'results': results,
                    'stats': stats
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


# 使用示例
if __name__ == "__main__":
    # 创建实例
    spider = SpiderJinzhengPages2mgo()
    
    # 默认运行（稳定模式，推荐）
    result = spider.run()
    print(f"默认模式结果: {result['stats']}")
    
    # 快速运行所有页面
    result = spider.quick_run()
    print(f"快速模式结果: {result['stats']}")
    
    # 稳定模式运行（推荐用于生产环境）
    stable_task = {
        'page_key': 'all',
        'browser': 'chromium',
        'headless': True,
        'stable_mode': True,  # 使用稳定模式
        'fast_mode': True
    }
    result = spider.run(stable_task)
    print(f"稳定模式结果: {result['stats']}")
    
    # 进程并行模式运行（高性能，使用进程池避免线程问题）
    parallel_task = {
        'page_key': 'all',
        'browser': 'chromium',
        'headless': True,
        'parallel': True,     # 使用进程池并行
        'max_workers': 2,     # 最大2个进程
        'fast_mode': True
    }
    result = spider.run(parallel_task)
    print(f"进程并行模式结果: {result['stats']}")
