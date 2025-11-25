#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P5现货应用决策（42天后）数据爬取测试脚本
用于验证 p5_spot_decision_42d 子任务的数据爬取功能是否正常工作
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


class P5DataValidator:
    """P5数据验证器"""
    
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
        """格式验证：检查数据是否包含P5特有关键词"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        # P5现货应用决策特有关键词
        p5_keywords = [
            "做空胜率统计",
            "盈亏比",
            "建议交易方向",
            "价差比区间",
            "预测值",
            "出现概率",
            "正收益",
            "负收益",
            "P5",
            "P5现货",
            "P5TC",
            "42天后",
            "做空",
            "做多",
            "综合价差比",
            "当期值",
            "预测值",
            "最大正收益",
            "最小负收益",
            "盈亏比"
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
        found_keywords = []
        for keyword in p5_keywords:
            if keyword in all_text:
                found_keywords.append(keyword)
        
        # 判断结果
        if len(found_keywords) >= 5:
            result["passed"] = True
            result["message"] = f"格式验证通过，找到 {len(found_keywords)} 个关键词"
        else:
            result["message"] = f"格式验证失败，仅找到 {len(found_keywords)} 个关键词（需要至少5个）"
        
        result["details"] = {
            "found_keywords": found_keywords,
            "total_keywords": len(p5_keywords),
            "found_count": len(found_keywords),
            "coverage": f"{len(found_keywords)}/{len(p5_keywords)}"
        }
        
        return result
    
    def validate_completeness(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """完整性验证：检查数据是否包含关键字段"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        # 检查是否有足够的表格
        if len(raw_data) < 1:
            result["message"] = "数据不完整：表格数量不足"
            return result
        
        # 检查每个表格是否有数据
        tables_with_data = 0
        total_rows = 0
        for table in raw_data:
            if isinstance(table, dict) and 'rows' in table:
                rows = table['rows']
                if len(rows) > 0:
                    tables_with_data += 1
                    total_rows += len(rows)
        
        if tables_with_data == 0:
            result["message"] = "数据不完整：没有包含数据的表格"
            return result
        
        result["passed"] = True
        result["message"] = "完整性验证通过"
        result["details"] = {
            "total_tables": len(raw_data),
            "tables_with_data": tables_with_data,
            "total_rows": total_rows,
            "average_rows_per_table": round(total_rows / tables_with_data, 2) if tables_with_data > 0 else 0
        }
        
        return result
    
    def validate_structure(self, raw_data: List[Dict]) -> Dict[str, Any]:
        """结构验证：检查数据结构的正确性"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        # 检查数据结构
        valid_tables = 0
        invalid_tables = 0
        
        for table in raw_data:
            if isinstance(table, dict):
                # 检查必要字段
                if 'rows' in table:
                    if isinstance(table['rows'], list):
                        valid_tables += 1
                    else:
                        invalid_tables += 1
                else:
                    invalid_tables += 1
            else:
                invalid_tables += 1
        
        if invalid_tables > 0:
            result["message"] = f"结构验证失败：发现 {invalid_tables} 个无效表格"
            result["details"] = {
                "valid_tables": valid_tables,
                "invalid_tables": invalid_tables
            }
            return result
        
        result["passed"] = True
        result["message"] = "结构验证通过"
        result["details"] = {
            "valid_tables": valid_tables,
            "invalid_tables": invalid_tables
        }
        
        return result
    
    def validate_all(self, raw_data: Optional[List[Dict]], formatted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """执行所有验证"""
        results = {}
        
        # 基础验证
        results["basic_validation"] = self.validate_basic(raw_data)
        
        if not results["basic_validation"]["passed"]:
            self.validation_results["overall_status"] = "failed"
            return results
        
        # 格式验证
        results["format_validation"] = self.validate_format(raw_data)
        
        # 完整性验证
        results["completeness_validation"] = self.validate_completeness(raw_data)
        
        # 结构验证
        results["structure_validation"] = self.validate_structure(raw_data)
        
        # 判断总体状态
        all_passed = all([
            results["basic_validation"]["passed"],
            results["format_validation"]["passed"],
            results["completeness_validation"]["passed"],
            results["structure_validation"]["passed"]
        ])
        
        self.validation_results["overall_status"] = "passed" if all_passed else "partial"
        results["overall_status"] = self.validation_results["overall_status"]
        
        return results


def test_p5_spot_decision_42d(headless: bool = False, save_file: bool = True) -> Dict[str, Any]:
    """测试P5现货应用决策（42天后）数据爬取的主函数"""
    
    print("=" * 80)
    print("P5现货应用决策（42天后）数据爬取测试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模式: {'无头模式' if headless else '有界面模式'}")
    print()
    
    # 创建任务实例
    spider = SpiderJinzhengPages2mgo()
    
    # 创建验证器
    validator = P5DataValidator()
    
    # 存储原始数据用于验证
    raw_data = None
    formatted_data = None
    
    try:
        # 执行数据抓取
        print("步骤 1: 开始抓取 p5_spot_decision_42d 页面数据...")
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
            raw_data = session.scrape_page("p5_spot_decision_42d")
            
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
            page_key="p5_spot_decision_42d",
            raw_data=raw_data,
            save_file=save_file,
            store_mongodb=False  # 测试时不存储到MongoDB
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
        formatted_data = spider.format_data("p5_spot_decision_42d", raw_data)
        
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
            
            status = "✓" if result.get("passed", False) else "✗"
            print(f"{status} {validation_name}: {result.get('message', '')}")
            if result.get("details"):
                for key, value in result["details"].items():
                    print(f"    {key}: {value}")
            print()
        
        print(f"总体状态: {validation_results.get('overall_status', 'unknown')}")
        print("=" * 80)
        
        # 显示数据摘要
        print("\n数据摘要:")
        print("-" * 80)
        if raw_data:
            total_rows = sum(len(table.get('rows', [])) for table in raw_data if isinstance(table, dict))
            print(f"总表格数: {len(raw_data)}")
            print(f"总行数: {total_rows}")
            
            # 显示前几个表格的信息
            for i, table in enumerate(raw_data[:3]):
                if isinstance(table, dict) and 'rows' in table:
                    rows = table['rows']
                    print(f"\n表格 {i+1}:")
                    print(f"  行数: {len(rows)}")
                    if rows:
                        print(f"  前3行示例:")
                        for j, row in enumerate(rows[:3]):
                            print(f"    行 {j+1}: {row[:5]}")  # 只显示前5个单元格
        
        return {
            "status": "success" if validation_results.get("overall_status") == "passed" else "partial",
            "validation_results": validation_results,
            "raw_data_stats": {
                "total_tables": len(raw_data) if raw_data else 0,
                "total_rows": sum(len(table.get('rows', [])) for table in raw_data if isinstance(table, dict) and 'rows' in table)
            },
            "formatted_data_available": formatted_data is not None
        }
        
    except Exception as e:
        import traceback
        print(f"✗ 测试过程中发生异常: {e}")
        print(traceback.format_exc())
        return {
            "status": "failed",
            "error": str(e),
            "validation_results": {}
        }


if __name__ == "__main__":
    # 运行测试（有界面模式，便于观察）
    result = test_p5_spot_decision_42d(headless=False, save_file=True)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print(f"状态: {result.get('status', 'unknown')}")
    
    if result.get("validation_results"):
        overall = result["validation_results"].get("overall_status", "unknown")
        print(f"验证结果: {overall}")

