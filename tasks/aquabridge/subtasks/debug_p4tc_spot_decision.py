#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P4TC现货应用决策数据爬取调试脚本
用于验证 p4tc_spot_decision 子任务的数据爬取功能是否正常工作
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 添加项目根目录到Python路径（用于导入pkg模块）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# 导入主任务类
from spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo


class P4TCDataValidator:
    """P4TC数据验证器"""
    
    def __init__(self):
        self.validation_results = {
            "basic_validation": {},
            "format_validation": {},
            "completeness_validation": {},
            "structure_validation": {},
            "overall_status": "unknown"
        }
    
    def validate_basic(self, raw_data: Optional[List[Dict]]) -> Dict[str, Any]:
        """基础验证：检查是否成功抓取到数据"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        if raw_data is None:
            result["message"] = "原始数据为 None"
            return result
        
        if not isinstance(raw_data, list):
            result["message"] = f"原始数据不是列表类型，而是 {type(raw_data)}"
            return result
        
        if len(raw_data) == 0:
            result["message"] = "原始数据为空列表"
            return result
        
        # 统计表格信息
        total_tables = len(raw_data)
        total_rows = 0
        for table in raw_data:
            if isinstance(table, dict) and 'rows' in table:
                total_rows += len(table['rows'])
        
        result["passed"] = True
        result["message"] = "基础验证通过"
        result["details"] = {
            "total_tables": total_tables,
            "total_rows": total_rows,
            "has_data": True
        }
        
        return result
    
    def validate_format(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """格式验证：检查数据是否包含P4TC特有关键词"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        # P4TC特有关键词
        p4tc_keywords = [
            "做空胜率统计",
            "盈亏比",
            "建议交易方向",
            "价差比区间",
            "预测值",
            "出现概率",
            "正收益",
            "负收益",
            "P4TC"
        ]
        
        # FFA关键词（用于区分）
        ffa_keywords = [
            "C5TC＋1",
            "P4TC＋1",
            "偏离度",
            "入场区间",
            "离场区间"
        ]
        
        # 收集所有文本内容
        all_text = ""
        for table in raw_data:
            if isinstance(table, dict) and 'rows' in table:
                for row in table['rows']:
                    if isinstance(row, list):
                        row_text = " ".join([str(cell) for cell in row if cell])
                        all_text += row_text + " "
        
        # 检查关键词
        found_p4tc_keywords = []
        found_ffa_keywords = []
        
        for keyword in p4tc_keywords:
            if keyword in all_text:
                found_p4tc_keywords.append(keyword)
        
        for keyword in ffa_keywords:
            if keyword in all_text:
                found_ffa_keywords.append(keyword)
        
        # 判断结果
        if len(found_p4tc_keywords) >= 3:  # 至少找到3个P4TC关键词
            result["passed"] = True
            result["message"] = f"格式验证通过，找到 {len(found_p4tc_keywords)} 个P4TC关键词"
        elif len(found_ffa_keywords) > 0:
            result["passed"] = False
            result["message"] = f"检测到FFA格式数据，可能抓取了错误的页面"
        else:
            result["passed"] = False
            result["message"] = f"未找到足够的P4TC关键词（仅找到 {len(found_p4tc_keywords)} 个）"
        
        result["details"] = {
            "found_p4tc_keywords": found_p4tc_keywords,
            "found_ffa_keywords": found_ffa_keywords,
            "total_p4tc_keywords": len(found_p4tc_keywords),
            "total_ffa_keywords": len(found_ffa_keywords)
        }
        
        return result
    
    def validate_completeness(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """完整性验证：检查数据行数、关键字段是否存在"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        # 统计信息
        total_tables = len(raw_data)
        total_rows = 0
        max_rows_in_table = 0
        min_rows_in_table = float('inf')
        
        for table in raw_data:
            if isinstance(table, dict) and 'rows' in table:
                rows_count = len(table['rows'])
                total_rows += rows_count
                max_rows_in_table = max(max_rows_in_table, rows_count)
                min_rows_in_table = min(min_rows_in_table, rows_count)
        
        # 检查是否有足够的数据
        # P4TC页面通常应该有至少20行数据
        min_expected_rows = 20
        
        if total_rows >= min_expected_rows:
            result["passed"] = True
            result["message"] = f"完整性验证通过，共有 {total_rows} 行数据"
        else:
            result["passed"] = False
            result["message"] = f"数据行数不足，期望至少 {min_expected_rows} 行，实际 {total_rows} 行"
        
        result["details"] = {
            "total_tables": total_tables,
            "total_rows": total_rows,
            "max_rows_in_table": max_rows_in_table if max_rows_in_table != 0 else 0,
            "min_rows_in_table": min_rows_in_table if min_rows_in_table != float('inf') else 0,
            "min_expected_rows": min_expected_rows
        }
        
        return result
    
    def validate_structure(self, formatted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """结构化验证：检查格式化后的数据结构是否完整"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        if formatted_data is None:
            result["message"] = "格式化数据为 None"
            return result
        
        if not isinstance(formatted_data, dict):
            result["message"] = f"格式化数据不是字典类型，而是 {type(formatted_data)}"
            return result
        
        # 检查必需的顶级字段
        required_fields = ["metadata", "contracts", "summary"]
        missing_fields = []
        
        for field in required_fields:
            if field not in formatted_data:
                missing_fields.append(field)
        
        if missing_fields:
            result["message"] = f"缺少必需的字段: {missing_fields}"
            return result
        
        # 检查metadata字段
        metadata = formatted_data.get("metadata", {})
        metadata_fields = ["timestamp", "browser", "page_name", "swap_date"]
        missing_metadata = [f for f in metadata_fields if f not in metadata]
        
        # 检查contracts字段
        contracts = formatted_data.get("contracts", {})
        has_raw_table_data = "raw_table_data" in contracts
        has_p4tc_analysis = "p4tc_analysis" in contracts
        
        # 检查summary字段
        summary = formatted_data.get("summary", {})
        
        # 判断结果
        issues = []
        if missing_metadata:
            issues.append(f"metadata缺少字段: {missing_metadata}")
        if not has_raw_table_data:
            issues.append("contracts中缺少raw_table_data")
        if not summary:
            issues.append("summary为空")
        
        if not issues:
            result["passed"] = True
            result["message"] = "结构化验证通过"
        else:
            result["message"] = "; ".join(issues)
        
        result["details"] = {
            "has_metadata": "metadata" in formatted_data,
            "has_contracts": "contracts" in formatted_data,
            "has_summary": "summary" in formatted_data,
            "missing_metadata_fields": missing_metadata,
            "has_raw_table_data": has_raw_table_data,
            "has_p4tc_analysis": has_p4tc_analysis,
            "contracts_keys": list(contracts.keys()) if contracts else [],
            "summary_keys": list(summary.keys()) if summary else []
        }
        
        return result
    
    def validate_all(self, raw_data: Optional[List[Dict]], formatted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """执行所有验证"""
        results = {}
        
        # 基础验证
        if raw_data is not None:
            results["basic"] = self.validate_basic(raw_data)
            results["format"] = self.validate_format(raw_data)
            results["completeness"] = self.validate_completeness(raw_data)
        else:
            results["basic"] = {"passed": False, "message": "原始数据为None，跳过其他验证"}
            results["format"] = {"passed": False, "message": "原始数据为None，跳过验证"}
            results["completeness"] = {"passed": False, "message": "原始数据为None，跳过验证"}
        
        # 结构化验证
        results["structure"] = self.validate_structure(formatted_data)
        
        # 计算总体状态
        all_passed = all(r.get("passed", False) for r in results.values())
        results["overall_status"] = "passed" if all_passed else "failed"
        
        return results


def debug_p4tc_spot_decision(headless: bool = False, save_file: bool = True) -> Dict[str, Any]:
    """调试p4tc_spot_decision任务的主函数"""
    
    print("=" * 80)
    print("P4TC现货应用决策数据爬取调试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模式: {'无头模式' if headless else '有界面模式'}")
    print()
    
    # 创建任务实例
    spider = SpiderJinzhengPages2mgo()
    
    # 创建验证器
    validator = P4TCDataValidator()
    
    # 存储原始数据用于验证
    raw_data = None
    formatted_data = None
    
    try:
        # 执行数据抓取
        print("步骤 1: 开始抓取 p4tc_spot_decision 页面数据...")
        print("-" * 80)
        
        # 使用SessionManager直接抓取原始数据
        try:
            from modules.session_manager import SessionManager
        except ImportError:
            # 如果相对导入失败，尝试绝对导入
            import sys
            modules_path = os.path.join(parent_dir, "modules")
            if modules_path not in sys.path:
                sys.path.insert(0, modules_path)
            from session_manager import SessionManager
        
        with SessionManager(browser_type="chromium", headless=headless) as session:
            # 登录
            if not session.login_once():
                print("✗ 登录失败")
                return {
                    "status": "failed",
                    "error": "登录失败",
                    "validation_results": {}
                }
            
            # 抓取数据
            raw_data = session.scrape_page("p4tc_spot_decision")
            
            if raw_data is None:
                print("✗ 数据抓取失败")
                return {
                    "status": "failed",
                    "error": "数据抓取失败",
                    "validation_results": {}
                }
            
            print(f"✓ 成功抓取到 {len(raw_data)} 个表格的数据")
            print()
        
        # 处理数据
        print("步骤 2: 处理数据...")
        print("-" * 80)
        
        success = spider._process_data(
            page_key="p4tc_spot_decision",
            raw_data=raw_data,
            save_file=save_file,
            store_mongodb=False  # 调试时不存储到MongoDB
        )
        
        if not success:
            print("✗ 数据处理失败")
            return {
                "status": "failed",
                "error": "数据处理失败",
                "raw_data_stats": {
                    "total_tables": len(raw_data) if raw_data else 0
                },
                "validation_results": {}
            }
        
        print("✓ 数据处理成功")
        print()
        
        # 获取格式化后的数据
        formatted_data = spider.format_data("p4tc_spot_decision", raw_data)
        
        # 执行验证
        print("步骤 3: 执行数据验证...")
        print("-" * 80)
        
        validation_results = validator.validate_all(raw_data, formatted_data)
        
        # 输出验证结果
        print("\n验证结果:")
        print("=" * 80)
        
        for validation_name, result in validation_results.items():
            if validation_name == "overall_status":
                continue
            
            status_icon = "✓" if result.get("passed", False) else "✗"
            print(f"{status_icon} {validation_name}: {result.get('message', 'N/A')}")
            
            if result.get("details"):
                for key, value in result["details"].items():
                    print(f"    - {key}: {value}")
        
        print()
        print(f"总体状态: {validation_results.get('overall_status', 'unknown')}")
        print("=" * 80)
        
        # 输出数据统计
        print("\n数据统计:")
        print("-" * 80)
        
        if raw_data:
            total_rows = sum(len(t.get('rows', [])) for t in raw_data if isinstance(t, dict))
            print(f"原始数据: {len(raw_data)} 个表格, {total_rows} 行")
        
        if formatted_data:
            contracts = formatted_data.get("contracts", {})
            raw_table = contracts.get("raw_table_data", {})
            print(f"格式化数据: {len(contracts)} 个合约/数据块")
            if raw_table:
                print(f"  - raw_table_data: {raw_table.get('total_rows', 0)} 行")
            if "p4tc_analysis" in contracts:
                print(f"  - p4tc_analysis: 已解析")
        
        print()
        
        # 保存验证报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "task": "p4tc_spot_decision",
            "status": "success" if validation_results.get("overall_status") == "passed" else "failed",
            "raw_data_stats": {
                "total_tables": len(raw_data) if raw_data else 0,
                "total_rows": sum(len(t.get('rows', [])) for t in raw_data if isinstance(t, dict)) if raw_data else 0
            },
            "validation_results": validation_results,
            "formatted_data_summary": {
                "has_metadata": "metadata" in formatted_data if formatted_data else False,
                "has_contracts": "contracts" in formatted_data if formatted_data else False,
                "has_summary": "summary" in formatted_data if formatted_data else False,
                "contracts_count": len(formatted_data.get("contracts", {})) if formatted_data else 0
            } if formatted_data else {}
        }
        
        # 保存报告到文件
        report_dir = "output"
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"p4tc_spot_decision_debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"验证报告已保存到: {report_file}")
        print()
        
        return report
        
    except Exception as e:
        print(f"✗ 发生异常: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "failed",
            "error": str(e),
            "raw_data_stats": {
                "total_tables": len(raw_data) if raw_data else 0
            },
            "validation_results": {}
        }
    
    finally:
        # 清理资源
        spider._close_mongodb()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="调试 p4tc_spot_decision 数据爬取任务")
    parser.add_argument("--headless", action="store_true", help="使用无头模式（默认：有界面模式）")
    parser.add_argument("--no-save", action="store_true", help="不保存输出文件")
    
    args = parser.parse_args()
    
    result = debug_p4tc_spot_decision(
        headless=args.headless,
        save_file=not args.no_save
    )
    
    # 输出最终状态
    print("\n" + "=" * 80)
    if result.get("status") == "success":
        print("✓ 调试完成：数据爬取正常")
    else:
        print("✗ 调试完成：发现问题")
        if "error" in result:
            print(f"错误: {result['error']}")
    print("=" * 80)

