#!/usr/bin/env python3
"""
双边交易机会汇总数据解析器
专门用于解析双边交易机会汇总页面的数据结构
包含三个部分：现货VS期货、现货VS现货、期货VS期货
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class BilateralTradingOpportunityParser:
    """双边交易机会汇总数据解析器"""
    
    def __init__(self):
        self.parsed_data = {}
    
    def parse_bilateral_trading_opportunity_data(self, rows: List[List[str]]) -> Dict[str, Any]:
        """解析双边交易机会汇总页面数据
        
        Args:
            rows: 表格行数据列表
            
        Returns:
            解析后的结构化数据字典，包含三个部分
        """
        if not rows:
            return {}
        
        # 将表格数据转换为文本进行分析
        text_data = self._rows_to_text(rows)
        
        # 解析各个部分
        self.parsed_data = {
            "metadata": {
                "page_name": "双边交易机会汇总",
                "parsed_at": datetime.now().isoformat(),
                "data_source": "AquaBridge"
            },
            "spot_vs_futures": {
                "date": self._extract_date_by_section(rows, text_data, "现货VS期货"),
                "opportunities": self._extract_opportunities_by_section(rows, text_data, "现货VS期货")
            },
            "spot_vs_spot": {
                "date": self._extract_date_by_section(rows, text_data, "现货VS现货"),
                "opportunities": self._extract_opportunities_by_section(rows, text_data, "现货VS现货")
            },
            "futures_vs_futures": {
                "date": self._extract_date_by_section(rows, text_data, "期货VS期货"),
                "opportunities": self._extract_opportunities_by_section(rows, text_data, "期货VS期货")
            }
        }
        
        return self.parsed_data
    
    def _rows_to_text(self, rows: List[List[str]]) -> str:
        """将表格行转换为文本"""
        text_lines = []
        for row in rows:
            # 过滤空单元格并连接
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if non_empty_cells:
                text_lines.append(" ".join(non_empty_cells))
        return "\n".join(text_lines)
    
    def _extract_date_by_section(self, rows: List[List[str]], text: str, section_name: str) -> Optional[str]:
        """提取指定部分的日期信息"""
        date = None
        
        # 查找部分开始位置
        section_start_index = -1
        for i, row in enumerate(rows):
            row_text = " ".join([cell.strip() for cell in row if cell.strip()])
            if section_name in row_text and len(row_text.strip()) <= 20:  # 确保是标题行
                section_start_index = i
                break
        
        # 在部分范围内查找日期
        if section_start_index >= 0:
            # 查找该部分及其后10行内的日期
            search_range = rows[section_start_index:section_start_index + 10]
            for row in search_range:
                for cell in row:
                    cell = cell.strip()
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cell)
                    if date_match:
                        date = date_match.group(1)
                        break
                if date:
                    break
        
        # 如果没找到，从整个文本中查找
        if not date:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if date_match:
                date = date_match.group(1)
        
        return date
    
    def _extract_opportunities_by_section(self, rows: List[List[str]], text: str, section_name: str) -> List[Dict[str, Any]]:
        """提取指定部分的交易机会数据
        
        Args:
            rows: 表格行数据列表
            text: 文本数据
            section_name: 部分名称（"现货VS期货"、"现货VS现货"、"期货VS期货"）
            
        Returns:
            交易机会列表
        """
        opportunities = []
        
        # 查找部分开始位置
        section_start_index = -1
        section_end_index = len(rows)
        
        for i, row in enumerate(rows):
            row_text = " ".join([cell.strip() for cell in row if cell.strip()])
            if section_name in row_text and len(row_text.strip()) <= 20:  # 确保是标题行
                section_start_index = i + 1  # 从下一行开始
                # 查找下一个部分或结束位置
                for j in range(i + 1, len(rows)):
                    next_row_text = " ".join([cell.strip() for cell in rows[j] if cell.strip()])
                    if ("现货VS期货" in next_row_text or "现货VS现货" in next_row_text or 
                        "期货VS期货" in next_row_text) and len(next_row_text.strip()) <= 20:
                        section_end_index = j
                        break
                break
        
        # 如果找到了部分开始位置，只在该范围内查找
        if section_start_index >= 0:
            search_rows = rows[section_start_index:section_end_index]
        else:
            # 如果没有找到明确的标记，在整个数据中查找
            search_rows = rows
        
        # 遍历指定范围的行，查找交易机会数据
        for i, row in enumerate(search_rows):
            # 将行转换为文本
            row_text = " ".join([cell.strip() for cell in row if cell.strip()])
            
            # 跳过空行和标题行
            if not row_text or section_name in row_text or len(row_text.strip()) < 5:
                continue
            
            # 检查这一行是否包含"VS"关键词（表示是交易机会行）
            if "VS" not in row_text and "vs" not in row_text.lower():
                continue
            
            # 提取资产对比（如 "P3A VS P4TC+1M"）
            asset_pair = None
            # 匹配模式：资产1 VS 资产2
            vs_pattern = r'([A-Z]\d+[A-Z]*[+\d]*M?)\s+VS\s+([A-Z]\d+[A-Z]*[+\d]*M?)'
            vs_match = re.search(vs_pattern, row_text, re.IGNORECASE)
            if vs_match:
                asset1 = vs_match.group(1)
                asset2 = vs_match.group(2)
                asset_pair = f"{asset1} VS {asset2}"
            
            if not asset_pair:
                continue
            
            # 提取组合交易方向（如 "P3A做空 P4TC+1M做多"）
            combined_direction = None
            # 尝试从行文本中提取交易方向
            # 模式1: 资产1做多/做空 资产2做多/做空
            direction_pattern = rf'({re.escape(asset1)}做[多空])\s*({re.escape(asset2)}做[多空])'
            direction_match = re.search(direction_pattern, row_text)
            if direction_match:
                combined_direction = f"{direction_match.group(1)} {direction_match.group(2)}"
            else:
                # 模式2: 从单元格数据中提取（如果行数据已经是解析好的格式）
                if len(row) >= 3:
                    # 检查是否有交易方向相关的单元格
                    direction_cells = [cell.strip() for cell in row if '做多' in cell or '做空' in cell]
                    if direction_cells:
                        combined_direction = " ".join(direction_cells)
            
            # 提取盈亏比（支持整数和小数）
            profit_loss_ratio = None
            # 首先尝试匹配 "数字: 1" 或 "数字：1" 格式
            ratio_patterns = [
                r'(\d+\.?\d+)\s*[:：]\s*1',      # 标准格式：9.99: 1 或 2082.73: 1
                r'(\d+\.?\d+)\s*[:：]1',        # 无空格格式：9.99:1
            ]
            
            for pattern in ratio_patterns:
                match = re.search(pattern, row_text)
                if match:
                    profit_loss_ratio = match.group(1)
                    break
            
            # 如果没找到，尝试从单元格数据中提取（如果行数据已经是解析好的格式）
            if not profit_loss_ratio and len(row) >= 3:
                # 检查最后一个单元格是否是盈亏比数字
                ratio_cell = row[-1].strip() if row else ''
                # 如果是纯数字或数字格式，直接使用
                if ratio_cell and re.match(r'^\d+\.?\d*$', ratio_cell):
                    profit_loss_ratio = ratio_cell
            
            # 如果找到了资产对比，记录这条交易机会
            if asset_pair:
                opportunity = {
                    "asset_pair": asset_pair,
                    "combined_direction": combined_direction,
                    "profit_loss_ratio": profit_loss_ratio
                }
                opportunities.append(opportunity)
        
        return opportunities


# 测试代码
if __name__ == "__main__":
    # 测试数据
    test_rows = [
        ["现货VS期货"],
        ["P3A", "VS", "P4TC+1M", "P3A做空", "P4TC+1M做多", "9.99: 1"],
        ["P5", "VS", "P4TC+1M", "P5做空", "P4TC+1M做多", "5.05: 1"],
        ["现货VS现货"],
        ["P6", "VS", "P3A", "P6做多", "P3A做空", "2082.73: 1"],
        ["期货VS期货"],
        ["C5TC+1M", "VS", "P4TC+1M", "C5TC+1M做空", "P4TC+1M做多", "5.13: 1"],
    ]
    
    parser = BilateralTradingOpportunityParser()
    result = parser.parse_bilateral_trading_opportunity_data(test_rows)
    
    import json
    print("=== 双边交易机会汇总数据解析结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

