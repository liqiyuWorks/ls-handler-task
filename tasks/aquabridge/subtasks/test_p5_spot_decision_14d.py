#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P5现货应用决策（14天后）数据爬取测试脚本
用于验证 p5_spot_decision_14d 子任务的数据爬取功能是否正常工作
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
    """P5数据验证器（支持14d和42d版本）"""
    
    def __init__(self):
        self.validation_results = {
            "basic_validation": {},
            "format_validation": {},
            "completeness_validation": {},
            "structure_validation": {},
            "version_validation": {},
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
    
    def validate_format(self, raw_data: List[Dict], page_name: str = "") -> Dict[str, Any]:
        """格式验证：检查数据是否包含P5特有关键词（区分14d和42d）"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        # P5现货应用决策特有关键词（14d版本）
        p5_keywords_14d = [
            "做空胜率统计",
            "盈亏比",
            "建议交易方向",
            "档位区间",  # 14d特有
            "综合价差比",
            "预测值",
            "出现概率",
            "正收益",
            "负收益",
            "P5",
            "P5现货",
            "P5TC",
            "14天后",
            "二周后",  # 14d特有
            "P5当前评估价格",  # 14d特有
            "P5TC二周后预测模型评价",  # 14d特有
            "预测14天后",  # 14d特有
            "做空",
            "做多"
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
        for keyword in p5_keywords_14d:
            if keyword in all_text:
                found_keywords.append(keyword)
        
        # 检查是否是14d版本
        is_14d = "14天后" in page_name or "14天" in all_text or "二周后" in all_text
        is_42d = "42天后" in page_name or "42天" in all_text or "六周后" in all_text
        
        # 判断结果
        if len(found_keywords) >= 5:
            result["passed"] = True
            result["message"] = f"格式验证通过，找到 {len(found_keywords)} 个关键词"
        else:
            result["message"] = f"格式验证失败，仅找到 {len(found_keywords)} 个关键词（需要至少5个）"
        
        result["details"] = {
            "found_keywords": found_keywords,
            "total_keywords": len(p5_keywords_14d),
            "found_count": len(found_keywords),
            "coverage": f"{len(found_keywords)}/{len(p5_keywords_14d)}",
            "is_14d": is_14d,
            "is_42d": is_42d,
            "version_detected": "14d" if is_14d else "42d" if is_42d else "unknown"
        }
        
        return result
    
    def validate_version(self, formatted_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """版本验证：检查数据是否包含14d版本特有的字段"""
        result = {
            "passed": False,
            "message": "",
            "details": {}
        }
        
        if not formatted_data or 'contracts' not in formatted_data:
            result["message"] = "格式化数据为空或缺少contracts字段"
            return result
        
        contracts = formatted_data.get('contracts', {})
        p5_analysis = contracts.get('p5_analysis', {})
        
        if not p5_analysis:
            result["message"] = "缺少p5_analysis数据"
            return result
        
        # 检查版本标识
        metadata = p5_analysis.get('metadata', {})
        version = metadata.get('version', 'unknown')
        
        # 检查14d版本特有字段
        has_14d_fields = 'p5_current_evaluation_price' in p5_analysis and 'p5tc_14d_model_evaluation' in p5_analysis
        has_42d_fields = 'p5_profit_loss_ratio' in p5_analysis and 'p5tc_model_evaluation' in p5_analysis
        
        if version == "14d" and has_14d_fields:
            result["passed"] = True
            result["message"] = "14d版本验证通过，包含所有特有字段"
        elif version == "42d" and has_42d_fields:
            result["passed"] = True
            result["message"] = "42d版本验证通过，包含所有特有字段"
        else:
            result["message"] = f"版本验证失败：版本={version}, 14d字段={has_14d_fields}, 42d字段={has_42d_fields}"
        
        result["details"] = {
            "version": version,
            "has_14d_fields": has_14d_fields,
            "has_42d_fields": has_42d_fields,
            "p5_current_evaluation_price": 'p5_current_evaluation_price' in p5_analysis,
            "p5tc_14d_model_evaluation": 'p5tc_14d_model_evaluation' in p5_analysis,
            "p5_profit_loss_ratio": 'p5_profit_loss_ratio' in p5_analysis,
            "p5tc_model_evaluation": 'p5tc_model_evaluation' in p5_analysis
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
    
    def validate_all(self, raw_data: Optional[List[Dict]], formatted_data: Optional[Dict[str, Any]], page_name: str = "") -> Dict[str, Any]:
        """执行所有验证"""
        results = {}
        
        # 基础验证
        results["basic_validation"] = self.validate_basic(raw_data)
        
        if not results["basic_validation"]["passed"]:
            self.validation_results["overall_status"] = "failed"
            return results
        
        # 格式验证
        results["format_validation"] = self.validate_format(raw_data, page_name)
        
        # 完整性验证
        results["completeness_validation"] = self.validate_completeness(raw_data)
        
        # 结构验证
        results["structure_validation"] = self.validate_structure(raw_data)
        
        # 版本验证
        results["version_validation"] = self.validate_version(formatted_data)
        
        # 判断总体状态
        all_passed = all([
            results["basic_validation"]["passed"],
            results["format_validation"]["passed"],
            results["completeness_validation"]["passed"],
            results["structure_validation"]["passed"],
            results["version_validation"]["passed"]
        ])
        
        self.validation_results["overall_status"] = "passed" if all_passed else "partial"
        results["overall_status"] = self.validation_results["overall_status"]
        
        return results


def test_p5_spot_decision_14d(headless: bool = False, save_file: bool = True) -> Dict[str, Any]:
    """测试P5现货应用决策（14天后）数据爬取的主函数"""
    
    print("=" * 80)
    print("P5现货应用决策（14天后）数据爬取测试")
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
        print("步骤 1: 开始抓取 p5_spot_decision_14d 页面数据...")
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
            raw_data = session.scrape_page("p5_spot_decision_14d")
            
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
            page_key="p5_spot_decision_14d",
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
        formatted_data = spider.format_data("p5_spot_decision_14d", raw_data)
        
        # 执行验证
        print("步骤 3: 执行数据验证...")
        print("-" * 80)
        
        page_name = spider.supported_pages.get("p5_spot_decision_14d", {}).get("name", "")
        validation_results = validator.validate_all(raw_data, formatted_data, page_name)
        
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
        
        # 显示解析后的数据结构
        if formatted_data and 'contracts' in formatted_data:
            p5_analysis = formatted_data['contracts'].get('p5_analysis', {})
            if p5_analysis:
                print(f"\n解析后的数据结构:")
                print(f"  版本: {p5_analysis.get('metadata', {}).get('version', 'unknown')}")
                print(f"  包含的字段: {list(p5_analysis.keys())}")
                
                # 检查14d特有字段
                if 'p5_current_evaluation_price' in p5_analysis:
                    print(f"  ✓ 包含 p5_current_evaluation_price (14d特有)")
                if 'p5tc_14d_model_evaluation' in p5_analysis:
                    print(f"  ✓ 包含 p5tc_14d_model_evaluation (14d特有)")
        
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
    result = test_p5_spot_decision_14d(headless=False, save_file=True)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print(f"状态: {result.get('status', 'unknown')}")
    
    if result.get("validation_results"):
        overall = result["validation_results"].get("overall_status", "unknown")
        print(f"验证结果: {overall}")

