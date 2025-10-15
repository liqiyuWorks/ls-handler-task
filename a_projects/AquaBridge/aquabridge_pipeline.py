#!/usr/bin/env python3
"""
AquaBridge 多页面数据管道
支持 ffa_price_signals 和 p4tc_spot_decision 两个页面的数据抓取、处理和存储
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from data_scraper import DataScraper
from enhanced_formatter import EnhancedFormatter
from mongodb_storage import MongoDBStorage, load_config
from session_manager import SessionManager


class AquaBridgePipeline:
    """AquaBridge 数据管道主类"""
    
    def __init__(self, config_file: str = "mongodb_config.json"):
        """初始化管道
        
        Args:
            config_file: MongoDB配置文件路径
        """
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
        """初始化MongoDB连接
        
        Args:
            page_key: 页面键，用于确定collection
        """
        if self.mongodb_enabled:
            try:
                self.storage = MongoDBStorage(self.config, page_key)
                print(f"✓ MongoDB连接已建立 (集合: {page_key}_data)")
            except Exception as e:
                print(f"⚠ MongoDB连接失败: {e}")
                self.mongodb_enabled = False
    
    def _close_mongodb(self):
        """关闭MongoDB连接"""
        if self.storage:
            self.storage.close()
            self.storage = None
    
    def scrape_page(self, page_key: str, browser: str = "firefox", headless: bool = False) -> Optional[List[Dict]]:
        """抓取指定页面的数据
        
        Args:
            page_key: 页面键 (ffa_price_signals 或 p4tc_spot_decision)
            browser: 浏览器类型
            headless: 是否无头模式
            
        Returns:
            抓取的原始数据或None
        """
        if page_key not in self.supported_pages:
            print(f"✗ 不支持的页面: {page_key}")
            print(f"支持的页面: {list(self.supported_pages.keys())}")
            return None
        
        print(f"=== 抓取页面: {self.supported_pages[page_key]['name']} ===")
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as playwright:
                scraper = DataScraper(headless=headless, browser_type=browser)
                scraper.create_browser(playwright)
                scraper.page = scraper.context.new_page()
                scraper.page.set_default_timeout(12000)
                scraper.page.set_default_navigation_timeout(15000)
                
                data = scraper.scrape_page_data(page_key)
                scraper.cleanup()
                return data
                
        except Exception as e:
            print(f"✗ 页面抓取失败: {e}")
            return None
    
    def format_data(self, page_key: str, raw_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """格式化数据
        
        Args:
            page_key: 页面键
            raw_data: 原始数据
            
        Returns:
            格式化后的数据或None
        """
        if page_key not in self.supported_pages:
            return None
        
        print(f"=== 格式化数据: {self.supported_pages[page_key]['name']} ===")
        
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
            
            if formatted_data and formatted_data.get('contracts'):
                contract_count = len(formatted_data.get('contracts', {}))
                print(f"✓ 数据格式化完成: {contract_count} 个合约")
                return formatted_data
            else:
                print("✗ 数据格式化失败")
                return None
                
        except Exception as e:
            print(f"✗ 数据格式化异常: {e}")
            return None
    
    def store_data(self, page_key: str, data: Dict[str, Any]) -> bool:
        """存储数据到MongoDB
        
        Args:
            page_key: 页面键
            data: 格式化后的数据
            
        Returns:
            存储是否成功
        """
        if not self.mongodb_enabled:
            print("⚠ MongoDB存储已禁用")
            return True
        
        print(f"=== 存储数据: {self.supported_pages[page_key]['name']} ===")
        
        try:
            self._init_mongodb(page_key)
            
            if not self.storage:
                print("✗ MongoDB连接不可用")
                return False
            
            # 添加页面标识到metadata
            if 'metadata' in data:
                data['metadata']['page_key'] = page_key
            else:
                data['page_key'] = page_key
                data['page_name'] = self.supported_pages[page_key]['name']
            
            success = self.storage.store_ffa_data(data)
            
            # 获取swap_date用于日志
            swap_date = data.get('metadata', {}).get('swap_date', data.get('swap_date', 'N/A'))
            
            if success:
                print(f"✓ 数据已存储到MongoDB集合 {page_key}_data: swap_date={swap_date}")
            else:
                print(f"✗ MongoDB存储失败: swap_date={swap_date}")
            
            return success
            
        except Exception as e:
            print(f"✗ 存储数据异常: {e}")
            return False
    
    def save_to_file(self, page_key: str, data: Dict[str, Any], output_dir: str = "output") -> str:
        """保存数据到文件
        
        Args:
            page_key: 页面键
            data: 格式化后的数据
            output_dir: 输出目录
            
        Returns:
            文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{page_key}_data_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 数据已保存到文件: {filepath}")
        return filepath
    
    def process_page(self, page_key: str, browser: str = "firefox", headless: bool = False, 
                    save_file: bool = True, store_mongodb: bool = True) -> bool:
        """处理单个页面的完整流程
        
        Args:
            page_key: 页面键
            browser: 浏览器类型
            headless: 是否无头模式
            save_file: 是否保存到文件
            store_mongodb: 是否存储到MongoDB
            
        Returns:
            处理是否成功
        """
        print(f"\n{'='*60}")
        print(f"开始处理页面: {self.supported_pages[page_key]['name']}")
        print(f"{'='*60}")
        
        # 1. 抓取数据
        raw_data = self.scrape_page(page_key, browser, headless)
        if not raw_data:
            return False
        
        # 2. 格式化数据
        formatted_data = self.format_data(page_key, raw_data)
        if not formatted_data:
            return False
        
        # 3. 保存到文件
        if save_file:
            self.save_to_file(page_key, formatted_data)
        
        # 4. 存储到MongoDB
        if store_mongodb:
            self.store_data(page_key, formatted_data)
        
        # 5. 显示摘要
        self._display_summary(page_key, formatted_data)
        
        print(f"✓ 页面处理完成: {self.supported_pages[page_key]['name']}")
        return True
    
    def process_all_pages(self, browser: str = "firefox", headless: bool = False,
                         save_file: bool = True, store_mongodb: bool = True) -> Dict[str, bool]:
        """处理所有支持的页面（优化版本，复用登录会话）
        
        Args:
            browser: 浏览器类型
            headless: 是否无头模式
            save_file: 是否保存到文件
            store_mongodb: 是否存储到MongoDB
            
        Returns:
            各页面处理结果
        """
        results = {}
        
        print(f"\n{'='*60}")
        print("开始处理所有页面（优化版本）")
        print(f"{'='*60}")
        
        # 使用会话管理器进行批量处理
        try:
            with SessionManager(browser_type=browser, headless=headless) as session:
                # 登录一次
                if not session.login_once():
                    print("✗ 登录失败，无法继续处理")
                    return {page_key: False for page_key in self.supported_pages.keys()}
                
                # 批量抓取所有页面
                page_keys = list(self.supported_pages.keys())
                raw_data_results = session.scrape_multiple_pages(page_keys)
                
                # 处理每个页面的数据
                for page_key in page_keys:
                    try:
                        raw_data = raw_data_results.get(page_key)
                        if raw_data:
                            # 格式化数据
                            formatted_data = self.format_data(page_key, raw_data)
                            if formatted_data:
                                # 保存到文件
                                if save_file:
                                    self.save_to_file(page_key, formatted_data)
                                
                                # 存储到MongoDB
                                if store_mongodb:
                                    self.store_data(page_key, formatted_data)
                                
                                # 显示摘要
                                self._display_summary(page_key, formatted_data)
                                
                                results[page_key] = True
                                print(f"✓ 页面 {page_key} 处理完成")
                            else:
                                print(f"✗ 页面 {page_key} 数据格式化失败")
                                results[page_key] = False
                        else:
                            print(f"✗ 页面 {page_key} 数据抓取失败")
                            results[page_key] = False
                            
                    except Exception as e:
                        print(f"✗ 处理页面 {page_key} 时发生异常: {e}")
                        results[page_key] = False
        
        except Exception as e:
            print(f"✗ 批量处理异常: {e}")
            results = {page_key: False for page_key in self.supported_pages.keys()}
        
        # 显示总体结果
        self._display_overall_results(results)
        
        return results
    
    def process_all_pages_legacy(self, browser: str = "firefox", headless: bool = False,
                                save_file: bool = True, store_mongodb: bool = True) -> Dict[str, bool]:
        """处理所有支持的页面（传统版本，每个页面独立登录）
        
        Args:
            browser: 浏览器类型
            headless: 是否无头模式
            save_file: 是否保存到文件
            store_mongodb: 是否存储到MongoDB
            
        Returns:
            各页面处理结果
        """
        results = {}
        
        print(f"\n{'='*60}")
        print("开始处理所有页面（传统版本）")
        print(f"{'='*60}")
        
        for page_key in self.supported_pages.keys():
            try:
                results[page_key] = self.process_page(
                    page_key, browser, headless, save_file, store_mongodb
                )
            except Exception as e:
                print(f"✗ 处理页面 {page_key} 时发生异常: {e}")
                results[page_key] = False
        
        # 显示总体结果
        self._display_overall_results(results)
        
        return results
    
    def _display_summary(self, page_key: str, data: Dict[str, Any]):
        """显示数据摘要"""
        print(f"\n=== {self.supported_pages[page_key]['name']} 数据摘要 ===")
        
        # 获取metadata信息
        metadata = data.get('metadata', {})
        print(f"时间戳: {metadata.get('timestamp', data.get('timestamp', 'N/A'))}")
        print(f"掉期日期: {metadata.get('swap_date', data.get('swap_date', 'N/A'))}")
        print(f"数据源: {metadata.get('data_source', 'N/A')}")
        print(f"版本: {metadata.get('version', 'N/A')}")
        
        contracts = data.get('contracts', {})
        print(f"合约数量: {len(contracts)}")
        
        # 显示合约详情
        for contract_name, contract_data in contracts.items():
            if isinstance(contract_data, dict) and 'contract_name' in contract_data:
                # FFA合约数据
                print(f"\n{contract_data['contract_name']}合约:")
                print(f"  预测值: {contract_data.get('predicted_value', 'N/A')}")
                print(f"  当前值: {contract_data.get('current_value', 'N/A')}")
                print(f"  偏离度: {contract_data.get('deviation', 'N/A')}")
                print(f"  入场区间: {contract_data.get('entry_range', 'N/A')}")
                print(f"  离场区间: {contract_data.get('exit_range', 'N/A')}")
                print(f"  操作建议: {contract_data.get('operation_suggestion', 'N/A')}")
                print(f"  月份: {contract_data.get('month', 'N/A')}")
                print(f"  天数: {contract_data.get('days', 'N/A')}")
            else:
                # 其他类型数据
                print(f"\n{contract_name}:")
                if isinstance(contract_data, dict):
                    for key, value in contract_data.items():
                        if key != 'data':  # 跳过原始数据，只显示摘要
                            print(f"  {key}: {value}")
        
        # 显示摘要信息
        summary = data.get('summary', {})
        if summary:
            print(f"\n数据摘要:")
            print(f"  总合约数: {summary.get('total_contracts', 0)}")
            print(f"  数据质量: {summary.get('data_quality', 'N/A')}")
            print(f"  数据类型: {summary.get('data_type', 'N/A')}")
    
    def _display_overall_results(self, results: Dict[str, bool]):
        """显示总体处理结果"""
        print(f"\n{'='*60}")
        print("总体处理结果")
        print(f"{'='*60}")
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        for page_key, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"{self.supported_pages[page_key]['name']}: {status}")
        
        print(f"\n总计: {success_count}/{total_count} 个页面处理成功")
        
        if self.mongodb_enabled:
            print("MongoDB存储: 已启用")
        else:
            print("MongoDB存储: 已禁用")
    
    def list_supported_pages(self):
        """列出支持的页面"""
        print("支持的页面:")
        for page_key, info in self.supported_pages.items():
            print(f"  {page_key}: {info['name']} - {info['description']}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_mongodb()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AquaBridge 多页面数据管道",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 处理所有页面（优化版本，复用登录）
  python3 aquabridge_pipeline.py --all
  
  # 处理所有页面（传统版本，独立登录）
  python3 aquabridge_pipeline.py --all-legacy
  
  # 处理特定页面
  python3 aquabridge_pipeline.py --page ffa_price_signals
  
  # 仅存储到MongoDB，不保存文件
  python3 aquabridge_pipeline.py --all --mongodb-only
  
  # 禁用MongoDB存储
  python3 aquabridge_pipeline.py --all --no-mongodb
        """
    )
    
    # 页面选择
    page_group = parser.add_mutually_exclusive_group(required=True)
    page_group.add_argument("--all", action="store_true", help="处理所有页面（优化版本，复用登录）")
    page_group.add_argument("--all-legacy", action="store_true", help="处理所有页面（传统版本，独立登录）")
    page_group.add_argument("--page", choices=["ffa_price_signals", "p4tc_spot_decision"], 
                           help="处理指定页面")
    page_group.add_argument("--list", action="store_true", help="列出支持的页面")
    
    # 浏览器配置
    parser.add_argument("--browser", "-b", default="firefox", 
                       choices=["firefox", "chromium", "webkit"],
                       help="浏览器类型 (默认: firefox)")
    parser.add_argument("--headless", action="store_true", help="无头模式运行")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口")
    
    # 存储配置
    parser.add_argument("--no-mongodb", action="store_true", help="禁用MongoDB存储")
    parser.add_argument("--mongodb-only", action="store_true", help="仅存储到MongoDB，不保存文件")
    parser.add_argument("--no-file", action="store_true", help="不保存到文件")
    
    # 其他配置
    parser.add_argument("--config", default="mongodb_config.json", help="MongoDB配置文件路径")
    
    args = parser.parse_args()
    
    # 处理列表命令
    if args.list:
        pipeline = AquaBridgePipeline(args.config)
        pipeline.list_supported_pages()
        return 0
    
    # 创建管道实例
    try:
        with AquaBridgePipeline(args.config) as pipeline:
            # 禁用MongoDB存储
            if args.no_mongodb:
                pipeline.mongodb_enabled = False
            
            # 确定存储选项
            save_file = not args.mongodb_only and not args.no_file
            store_mongodb = not args.no_mongodb
            
            # 确定显示模式
            headless = args.headless and not args.no_headless
            
            # 处理页面
            if args.all:
                results = pipeline.process_all_pages(
                    browser=args.browser,
                    headless=headless,
                    save_file=save_file,
                    store_mongodb=store_mongodb
                )
                
                # 返回状态码
                success_count = sum(1 for success in results.values() if success)
                return 0 if success_count > 0 else 1
                
            elif args.all_legacy:
                results = pipeline.process_all_pages_legacy(
                    browser=args.browser,
                    headless=headless,
                    save_file=save_file,
                    store_mongodb=store_mongodb
                )
                
                # 返回状态码
                success_count = sum(1 for success in results.values() if success)
                return 0 if success_count > 0 else 1
                
            elif args.page:
                success = pipeline.process_page(
                    page_key=args.page,
                    browser=args.browser,
                    headless=headless,
                    save_file=save_file,
                    store_mongodb=store_mongodb
                )
                return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\n用户中断")
        return 1
    except Exception as e:
        print(f"\n管道执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
