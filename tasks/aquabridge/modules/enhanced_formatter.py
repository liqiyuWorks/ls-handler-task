#!/usr/bin/env python3
"""
增强型数据格式化器
能够正确解析页面数据并生成可读性强的JSON格式
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
try:
    from .p4tc_parser import P4TCParser
    from .p5_parser import P5Parser
    from .european_line_parser import EuropeanLineParser
except ImportError:
    from p4tc_parser import P4TCParser
    from p5_parser import P5Parser
    from european_line_parser import EuropeanLineParser


class EnhancedFormatter:
    """增强型数据格式化器"""
    
    def __init__(self):
        self.contracts = {}
        self.page_name = ""
    
    def format_data(self, raw_data: Dict) -> Dict[str, Any]:
        """格式化数据"""
        if not raw_data or 'tables' not in raw_data:
            return {}
        
        self.page_name = raw_data.get('page_name', '')
        tables = raw_data['tables']
        
        if not tables or not tables[0].get('rows'):
            return {}
        
        rows = tables[0]['rows']
        
        # 提取掉期日期
        swap_date = self._extract_swap_date(tables[0], rows)
        
        # 根据页面类型提取数据
        if 'FFA价格信号' in self.page_name:
            self._extract_ffa_contracts(rows)
        elif 'P4TC现货应用决策' in self.page_name:
            # P4TC页面需要传递原始表格数据
            self._extract_p4tc_data(tables)
        elif 'P5现货应用决策' in self.page_name or 'P5' in self.page_name:
            # P5页面需要传递原始表格数据，与P4TC区分开来
            self._extract_p5_data(tables)
        elif '欧线' in self.page_name or '欧线价格信号' in self.page_name:
            # 欧线页面使用专门的解析器
            self._extract_european_line_data(rows)
        else:
            self._extract_generic_data(rows)
        
        return {
            "metadata": {
                "timestamp": raw_data.get('timestamp', ''),
                "browser": raw_data.get('browser', ''),
                "page_name": self.page_name,
                "swap_date": swap_date,
                "data_source": "AquaBridge",
                "version": "1.0"
            },
            "contracts": self.contracts,
            "summary": self._generate_summary()
        }
    
    def _extract_swap_date(self, table_metadata: Dict, rows: List[List[str]]) -> str:
        """提取掉期日期"""
        # 首先检查表格元数据
        if 'swap_date' in table_metadata:
            return table_metadata['swap_date']
        
        # 从表格内容中查找日期
        for row in rows:
            for cell in row:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cell)
                if date_match:
                    return date_match.group(1)
        
        # 默认返回当前日期
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_ffa_contracts(self, rows: List[List[str]]):
        """提取FFA合约数据"""
        # 查找C5TC+1和P4TC+1合约数据（注意使用全角加号）
        c5tc_data = self._parse_contract_data(rows, "C5TC＋1")
        p4tc_data = self._parse_contract_data(rows, "P4TC＋1")
        
        if c5tc_data:
            # 将全角加号转换为半角加号用于存储
            c5tc_data["contract_name"] = "C5TC+1"
            self.contracts["C5TC+1"] = c5tc_data
        if p4tc_data:
            # 将全角加号转换为半角加号用于存储
            p4tc_data["contract_name"] = "P4TC+1"
            self.contracts["P4TC+1"] = p4tc_data
    
    def _parse_contract_data(self, rows: List[List[str]], contract_name: str) -> Optional[Dict[str, Any]]:
        """解析合约数据"""
        contract_data = {
            "contract_name": contract_name,
            "predicted_value": None,
            "current_value": None,
            "deviation": None,
            "entry_range": None,
            "exit_range": None,
            "operation_suggestion": None,
            "month": None,
            "days": None
        }
        
        # 查找合约标识行
        contract_row = None
        for i, row in enumerate(rows):
            if contract_name in ' '.join(row):
                contract_row = i
                break
        
        if contract_row is None:
            return None
        
        # 提取月份和天数
        contract_row_data = rows[contract_row]
        for j, cell in enumerate(contract_row_data):
            if contract_name in cell:
                # 查找月份 (Nov, Dec, etc.)
                for k in range(j, min(j + 5, len(contract_row_data))):
                    month_match = re.search(r'([A-Za-z]{3})', contract_row_data[k])
                    if month_match:
                        contract_data["month"] = month_match.group(1)
                        break
                
                # 查找天数
                for k in range(j, min(j + 5, len(contract_row_data))):
                    days_match = re.search(r'(\d{1,2})', contract_row_data[k])
                    if days_match:
                        contract_data["days"] = days_match.group(1)
                        break
                break
        
        # 查找预测值和当前值 - 改进逻辑
        for i in range(contract_row, min(contract_row + 8, len(rows))):
            row = rows[i]
            row_text = ' '.join(row)
            
            # 查找包含预测值和当前值的行
            if "预测值" in row_text and "当前值" in row_text:
                # 下一行应该包含数值
                if i + 1 < len(rows):
                    value_row = rows[i + 1]
                    values = []
                    for cell in value_row:
                        cell = cell.strip()
                        # 查找数字（包括小数）
                        if cell and re.match(r'^\d+(\.\d+)?$', cell):
                            values.append(cell)
                    
                    if len(values) >= 2:
                        contract_data["predicted_value"] = values[0]
                        contract_data["current_value"] = values[1]
                    elif len(values) == 1:
                        contract_data["predicted_value"] = values[0]
                break
        
        # 查找偏离度和区间信息 - 改进逻辑
        for i in range(contract_row, min(contract_row + 12, len(rows))):
            row = rows[i]
            row_text = ' '.join(row)
            
            if "偏离度" in row_text:
                # 下一行应该包含偏离度、区间和操作建议
                if i + 1 < len(rows):
                    data_row = rows[i + 1]
                    data_values = []
                    for cell in data_row:
                        cell = cell.strip()
                        if cell:  # 收集所有非空值
                            data_values.append(cell)
                    
                    # 解析数据值
                    for cell in data_values:
                        if "%" in cell and not contract_data["deviation"]:
                            contract_data["deviation"] = cell
                        elif "<" in cell and not contract_data["entry_range"]:
                            contract_data["entry_range"] = cell
                        elif ">" in cell and not contract_data["exit_range"]:
                            contract_data["exit_range"] = cell
                        elif any(keyword in cell for keyword in ["持有多单", "空仓", "平空", "开多", "开空", "平多"]):
                            contract_data["operation_suggestion"] = cell
                break
        
        # 如果还没有找到预测值和当前值，尝试从其他行查找
        if not contract_data["predicted_value"] or not contract_data["current_value"]:
            for i in range(contract_row, min(contract_row + 8, len(rows))):
                row = rows[i]
                values = []
                for cell in row:
                    cell = cell.strip()
                    # 查找数字（包括小数）
                    if cell and re.match(r'^\d+(\.\d+)?$', cell):
                        values.append(cell)
                
                if len(values) >= 2:
                    if not contract_data["predicted_value"]:
                        contract_data["predicted_value"] = values[0]
                    if not contract_data["current_value"]:
                        contract_data["current_value"] = values[1]
                    break
        
        # 验证数据完整性
        if contract_data["predicted_value"] and contract_data["current_value"]:
            return contract_data
        
        return None
    
    def _extract_p4tc_data(self, raw_data: List[Dict]):
        """提取P4TC页面数据"""
        # 从原始数据中提取所有表格行
        all_rows = []
        for table in raw_data:
            if 'rows' in table:
                all_rows.extend(table['rows'])
        
        if not all_rows:
            # 如果没有表格数据，返回空结果
            self.contracts["raw_table_data"] = {
                "description": "P4TC现货应用决策原始数据",
                "total_rows": 0,
                "data": [],
                "last_updated": datetime.now().isoformat()
            }
            return
        
        # 总是保存原始表格数据
        table_data = []
        for row in all_rows:
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if non_empty_cells:
                table_data.append(non_empty_cells)
        
        if table_data:
            self.contracts["raw_table_data"] = {
                "description": "P4TC现货应用决策原始数据",
                "total_rows": len(table_data),
                "data": table_data,
                "last_updated": datetime.now().isoformat()
            }
        
        # 检查数据格式 - 更严格的检测逻辑
        data_text = " ".join([" ".join(row) for row in all_rows])
        
        # 检查是否包含P4TC特有的关键词
        p4tc_keywords = ["做空胜率统计", "盈亏比", "建议交易方向", "价差比区间", "预测值", "出现概率"]
        has_p4tc_keywords = any(keyword in data_text for keyword in p4tc_keywords)
        
        # 检查是否包含FFA特有的关键词
        ffa_keywords = ["C5TC＋1", "P4TC＋1", "预测值", "当前值", "偏离度", "入场区间", "离场区间"]
        has_ffa_keywords = any(keyword in data_text for keyword in ffa_keywords)
        
        print(f"数据检测: P4TC关键词={has_p4tc_keywords}, FFA关键词={has_ffa_keywords}")
        print(f"数据行数: {len(all_rows)}")
        
        if has_ffa_keywords and not has_p4tc_keywords:
            print("⚠ 检测到FFA格式数据，使用FFA解析器")
            # 使用FFA解析器处理这种数据
            self._extract_ffa_contracts(all_rows)
        elif has_p4tc_keywords:
            print("✓ 检测到P4TC格式数据，使用P4TC解析器")
            # 使用专门的P4TC解析器
            parser = P4TCParser()
            parsed_data = parser.parse_p4tc_data(all_rows)
            
            if parsed_data and any(parsed_data.get(key) for key in ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'model_evaluation']):
                # 将解析后的数据存储到contracts中
                self.contracts["p4tc_analysis"] = parsed_data
        else:
            print("⚠ 未检测到明确的页面格式，尝试P4TC解析器")
            # 默认尝试P4TC解析器
            parser = P4TCParser()
            parsed_data = parser.parse_p4tc_data(all_rows)
            
            if parsed_data and any(parsed_data.get(key) for key in ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'model_evaluation']):
                # 将解析后的数据存储到contracts中
                self.contracts["p4tc_analysis"] = parsed_data
    
    def _extract_p5_data(self, raw_data: List[Dict]):
        """提取P5页面数据（与P4TC区分开来）"""
        # 从原始数据中提取所有表格行
        all_rows = []
        for table in raw_data:
            if 'rows' in table:
                all_rows.extend(table['rows'])
        
        if not all_rows:
            # 如果没有表格数据，返回空结果
            self.contracts["raw_table_data"] = {
                "description": "P5现货应用决策原始数据",
                "total_rows": 0,
                "data": [],
                "last_updated": datetime.now().isoformat()
            }
            return
        
        # 总是保存原始表格数据
        table_data = []
        for row in all_rows:
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if non_empty_cells:
                table_data.append(non_empty_cells)
        
        if table_data:
            self.contracts["raw_table_data"] = {
                "description": "P5现货应用决策原始数据",
                "total_rows": len(table_data),
                "data": table_data,
                "last_updated": datetime.now().isoformat()
            }
        
        # 检查数据格式 - 更严格的检测逻辑，确保是P5数据而不是P4TC
        data_text = " ".join([" ".join(row) for row in all_rows])
        
        # 检查是否包含P5特有的关键词（包括14d和42d版本）
        p5_keywords = [
            "P5现货", "P5现货应用决策", "P5TC", "P5盈亏比", 
            "P5TC六周后预测模型评价", "P5TC二周后预测模型评价",
            "P5当前评估价格", "预测14天后", "预测42天后"
        ]
        has_p5_keywords = any(keyword in data_text for keyword in p5_keywords)
        
        # 检查是否包含P4TC特有的关键词（用于区分）
        p4tc_keywords = ["P4TC现货", "P4TC现货应用决策", "P4TC六周后预测模型评价"]
        has_p4tc_keywords = any(keyword in data_text for keyword in p4tc_keywords)
        
        print(f"数据检测: P5关键词={has_p5_keywords}, P4TC关键词={has_p4tc_keywords}")
        print(f"数据行数: {len(all_rows)}")
        
        if has_p5_keywords and not has_p4tc_keywords:
            print("✓ 检测到P5格式数据，使用P5解析器")
            # 使用专门的P5解析器，传递页面名称以区分14d和42d
            parser = P5Parser()
            parsed_data = parser.parse_p5_data(all_rows, self.page_name)
            
            # 检查解析结果，支持14d和42d的不同数据结构
            valid_keys_42d = ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'p5_profit_loss_ratio', 'p5tc_model_evaluation']
            valid_keys_14d = ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'p5_current_evaluation_price', 'p5tc_14d_model_evaluation']
            
            if parsed_data and (any(parsed_data.get(key) for key in valid_keys_42d) or any(parsed_data.get(key) for key in valid_keys_14d)):
                # 将解析后的数据存储到contracts中
                self.contracts["p5_analysis"] = parsed_data
        elif has_p4tc_keywords:
            print("⚠ 检测到P4TC格式数据，但页面名称是P5，使用P5解析器")
            # 即使有P4TC关键词，但页面名称是P5，仍然使用P5解析器
            parser = P5Parser()
            parsed_data = parser.parse_p5_data(all_rows, self.page_name)
            
            valid_keys_42d = ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'p5_profit_loss_ratio', 'p5tc_model_evaluation']
            valid_keys_14d = ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'p5_current_evaluation_price', 'p5tc_14d_model_evaluation']
            
            if parsed_data and (any(parsed_data.get(key) for key in valid_keys_42d) or any(parsed_data.get(key) for key in valid_keys_14d)):
                self.contracts["p5_analysis"] = parsed_data
        else:
            print("⚠ 未检测到明确的页面格式，尝试P5解析器")
            # 默认尝试P5解析器
            parser = P5Parser()
            parsed_data = parser.parse_p5_data(all_rows, self.page_name)
            
            valid_keys_42d = ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'p5_profit_loss_ratio', 'p5tc_model_evaluation']
            valid_keys_14d = ['trading_recommendation', 'current_forecast', 'positive_returns', 'negative_returns', 'p5_current_evaluation_price', 'p5tc_14d_model_evaluation']
            
            if parsed_data and (any(parsed_data.get(key) for key in valid_keys_42d) or any(parsed_data.get(key) for key in valid_keys_14d)):
                # 将解析后的数据存储到contracts中
                self.contracts["p5_analysis"] = parsed_data
    
    def _extract_european_line_data(self, rows: List[List[str]]):
        """提取欧线页面数据"""
        # 使用专门的欧线解析器
        parser = EuropeanLineParser()
        parsed_data = parser.parse_european_line_data(rows)
        
        if parsed_data and any(parsed_data.get(key) for key in ['price_signals', 'trading_ranges', 'operation_suggestion', 'closing_price_date']):
            # 将解析后的数据存储到contracts中
            self.contracts["european_line_analysis"] = parsed_data
            
            # 同时保存原始表格数据以便调试
            table_data = []
            for row in rows:
                non_empty_cells = [cell.strip() for cell in row if cell.strip()]
                if non_empty_cells:
                    table_data.append(non_empty_cells)
            
            if table_data:
                self.contracts["raw_table_data"] = {
                    "description": "欧线价格信号原始数据",
                    "total_rows": len(table_data),
                    "data": table_data,
                    "last_updated": datetime.now().isoformat()
                }
    
    def _extract_generic_data(self, rows: List[List[str]]):
        """提取通用数据"""
        # 对于其他页面类型，提取所有有数据的行
        table_data = []
        
        for row in rows:
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if non_empty_cells:
                table_data.append(non_empty_cells)
        
        if table_data:
            self.contracts["raw_data"] = {
                "description": f"{self.page_name}原始数据",
                "total_rows": len(table_data),
                "data": table_data,
                "last_updated": datetime.now().isoformat()
            }
    
    def _clean_number(self, value: str) -> str:
        """清理数值"""
        if not value:
            return ""
        
        # 移除非数字字符，保留小数点和负号
        cleaned = re.sub(r'[^\d.-]', '', str(value))
        return cleaned if cleaned else value.strip()
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成数据摘要"""
        summary = {
            "total_contracts": len(self.contracts),
            "contract_names": list(self.contracts.keys()),
            "data_quality": "high" if self.contracts else "low"
        }
        
        # 为FFA页面添加特定摘要
        if 'FFA价格信号' in self.page_name:
            ffa_contracts = [k for k in self.contracts.keys() if k in ['C5TC+1', 'P4TC+1']]
            summary["ffa_contracts"] = ffa_contracts
            summary["data_type"] = "FFA价格信号"
        elif 'P4TC现货应用决策' in self.page_name:
            summary["data_type"] = "P4TC现货应用决策"
            summary["table_rows"] = self.contracts.get("table_data", {}).get("total_rows", 0)
        elif '欧线' in self.page_name or '欧线价格信号' in self.page_name:
            summary["data_type"] = "欧线价格信号"
            if "european_line_analysis" in self.contracts:
                analysis = self.contracts["european_line_analysis"]
                summary["has_price_signals"] = bool(analysis.get("price_signals"))
                summary["has_trading_ranges"] = bool(analysis.get("trading_ranges"))
                summary["has_operation_suggestion"] = bool(analysis.get("operation_suggestion"))
                summary["has_closing_price_date"] = bool(analysis.get("closing_price_date"))
        else:
            summary["data_type"] = "通用数据"
        
        return summary


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 enhanced_formatter.py <input_file> [output_file]")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output/enhanced_structured.json"
    
    print("=== 增强型数据格式化器 ===")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print()
    
    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 格式化数据
    formatter = EnhancedFormatter()
    structured_data = formatter.format_data(raw_data)
    
    # 保存数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)
    
    print("✓ 增强型结构化数据已保存")
    print("\n=== 格式化结果 ===")
    print(json.dumps(structured_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
