#!/usr/bin/env python3
"""
欧线价格信号数据解析器
专门用于解析欧线页面的数据结构
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class EuropeanLineParser:
    """欧线价格信号数据解析器"""
    
    def __init__(self):
        self.parsed_data = {}
    
    def parse_european_line_data(self, rows: List[List[str]]) -> Dict[str, Any]:
        """解析欧线页面数据
        
        Args:
            rows: 表格行数据列表
            
        Returns:
            解析后的结构化数据字典
        """
        if not rows:
            return {}
        
        # 将表格数据转换为文本进行分析
        text_data = self._rows_to_text(rows)
        
        # 解析各个部分
        self.parsed_data = {
            "metadata": {
                "page_name": "欧线价格信号",
                "parsed_at": datetime.now().isoformat(),
                "data_source": "AquaBridge"
            },
            "price_signals": self._extract_price_signals(rows, text_data),
            "trading_ranges": self._extract_trading_ranges(rows, text_data),
            "operation_suggestion": self._extract_operation_suggestion(rows, text_data),
            "closing_price_date": self._extract_closing_price_date(rows, text_data)
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
    
    def _extract_price_signals(self, rows: List[List[str]], text: str) -> Dict[str, Any]:
        """提取价格信号数据（预测值、当前值、偏离度）"""
        signals = {
            "predicted_value": None,
            "current_value": None,
            "deviation": None
        }
        
        # 方法1: 从表格行中查找包含"预测值"、"当前值"、"偏离度"的行
        for i, row in enumerate(rows):
            row_text = " ".join(row)
            
            # 查找包含标签的行
            if "预测值" in row_text or "当前值" in row_text or "偏离度" in row_text:
                # 检查下一行是否包含数值
                if i + 1 < len(rows):
                    value_row = rows[i + 1]
                    values = []
                    for cell in value_row:
                        cell = cell.strip()
                        if cell:
                            values.append(cell)
                    
                    # 尝试从值行中提取数据
                    for j, val in enumerate(values):
                        # 预测值通常是第一个数字
                        if not signals["predicted_value"] and re.match(r'^\d+(\.\d+)?$', val):
                            signals["predicted_value"] = val
                        # 偏离度包含百分号
                        elif "%" in val and not signals["deviation"]:
                            signals["deviation"] = val
                        # 当前值通常是较大的数字（可能包含小数）
                        elif re.match(r'^\d+(\.\d+)?$', val) and not signals["current_value"]:
                            # 如果已经有预测值，这个可能是当前值
                            if signals["predicted_value"]:
                                signals["current_value"] = val
        
        # 方法2: 从文本中直接提取
        # 提取预测值
        if not signals["predicted_value"]:
            predicted_patterns = [
                r'预测值[：:]\s*(\d+(?:\.\d+)?)',
                r'预测值\s+(\d+(?:\.\d+)?)',
                r'(\d{4})\s*预测值',  # 1569 预测值
            ]
            for pattern in predicted_patterns:
                match = re.search(pattern, text)
                if match:
                    signals["predicted_value"] = match.group(1)
                    break
        
        # 提取当前值
        if not signals["current_value"]:
            current_patterns = [
                r'当前值[：:]\s*(\d+(?:\.\d+)?)',
                r'当前值\s+(\d+(?:\.\d+)?)',
                r'(\d{4}\.\d+)\s*当前值',  # 1773.9 当前值
            ]
            for pattern in current_patterns:
                match = re.search(pattern, text)
                if match:
                    signals["current_value"] = match.group(1)
                    break
        
        # 提取偏离度
        if not signals["deviation"]:
            deviation_patterns = [
                r'偏离度[：:]\s*(\d+%)',
                r'偏离度\s+(\d+%)',
                r'(\d+%)\s*偏离度',
            ]
            for pattern in deviation_patterns:
                match = re.search(pattern, text)
                if match:
                    signals["deviation"] = match.group(1)
                    break
        
        # 方法3: 从表格中查找数值卡片（根据页面布局）
        # 页面通常有三个卡片：预测值、偏离度、当前值
        card_values = []
        for row in rows:
            for cell in row:
                cell = cell.strip()
                # 查找数字（可能是预测值或当前值）
                if re.match(r'^\d{3,5}(?:\.\d+)?$', cell):
                    card_values.append(cell)
                # 查找百分比（偏离度）
                elif re.match(r'^\d+%$', cell):
                    if not signals["deviation"]:
                        signals["deviation"] = cell
        
        # 如果找到了多个数值，按顺序分配
        if card_values:
            if len(card_values) >= 1 and not signals["predicted_value"]:
                signals["predicted_value"] = card_values[0]
            if len(card_values) >= 2 and not signals["current_value"]:
                signals["current_value"] = card_values[-1]  # 当前值通常是最后一个
        
        return signals
    
    def _extract_trading_ranges(self, rows: List[List[str]], text: str) -> Dict[str, Any]:
        """提取交易区间数据（开空入场区间、平空离场区间）"""
        ranges = {
            "short_entry_range": None,  # 开空入场区间
            "short_exit_range": None     # 平空离场区间
        }
        
        # 方法1: 从表格行中查找
        for i, row in enumerate(rows):
            row_text = " ".join(row)
            
            # 查找包含"开空入场区间"或"平空离场区间"的行
            if "开空入场区间" in row_text or "平空离场区间" in row_text:
                # 检查当前行或下一行是否包含区间值
                search_rows = [row]
                if i + 1 < len(rows):
                    search_rows.append(rows[i + 1])
                
                for search_row in search_rows:
                    for cell in search_row:
                        cell = cell.strip()
                        # 开空入场区间通常包含">"符号
                        if ">" in cell and not ranges["short_entry_range"]:
                            ranges["short_entry_range"] = cell
                        # 平空离场区间通常包含"<"符号
                        elif "<" in cell and not ranges["short_exit_range"]:
                            ranges["short_exit_range"] = cell
        
        # 方法2: 从文本中直接提取
        if not ranges["short_entry_range"]:
            entry_patterns = [
                r'开空入场区间[：:]\s*([><]\d+)',
                r'开空入场区间\s+([><]\d+)',
                r'([>]\d+)\s*开空入场',
            ]
            for pattern in entry_patterns:
                match = re.search(pattern, text)
                if match:
                    ranges["short_entry_range"] = match.group(1)
                    break
        
        if not ranges["short_exit_range"]:
            exit_patterns = [
                r'平空离场区间[：:]\s*([><]\d+)',
                r'平空离场区间\s+([><]\d+)',
                r'([<]\d+)\s*平空离场',
            ]
            for pattern in exit_patterns:
                match = re.search(pattern, text)
                if match:
                    ranges["short_exit_range"] = match.group(1)
                    break
        
        # 方法3: 直接搜索包含">"和"<"的数值
        if not ranges["short_entry_range"] or not ranges["short_exit_range"]:
            for row in rows:
                for cell in row:
                    cell = cell.strip()
                    if ">" in cell and cell[1:].isdigit():
                        if not ranges["short_entry_range"]:
                            ranges["short_entry_range"] = cell
                    elif "<" in cell and cell[1:].isdigit():
                        if not ranges["short_exit_range"]:
                            ranges["short_exit_range"] = cell
        
        return ranges
    
    def _extract_operation_suggestion(self, rows: List[List[str]], text: str) -> Optional[str]:
        """提取操作建议"""
        suggestion = None
        
        # 方法1: 从表格行中查找
        for row in rows:
            row_text = " ".join(row)
            
            # 查找包含"操作建议"的行
            if "操作建议" in row_text:
                # 检查当前行或下一行
                search_rows = [row]
                row_index = rows.index(row)
                if row_index + 1 < len(rows):
                    search_rows.append(rows[row_index + 1])
                
                for search_row in search_rows:
                    for cell in search_row:
                        cell = cell.strip()
                        # 操作建议通常是：平空、开空、平多、开多等
                        if any(keyword in cell for keyword in ["平空", "开空", "平多", "开多", "持有多单", "空仓"]):
                            suggestion = cell
                            break
                
                if suggestion:
                    break
        
        # 方法2: 从文本中直接提取
        if not suggestion:
            suggestion_patterns = [
                r'操作建议[：:]\s*(平空|开空|平多|开多|持有多单|空仓)',
                r'操作建议\s+(平空|开空|平多|开多|持有多单|空仓)',
                r'(平空|开空|平多|开多|持有多单|空仓)\s*操作建议',
            ]
            for pattern in suggestion_patterns:
                match = re.search(pattern, text)
                if match:
                    suggestion = match.group(1)
                    break
        
        # 方法3: 直接搜索关键词
        if not suggestion:
            keywords = ["平空", "开空", "平多", "开多", "持有多单", "空仓"]
            for keyword in keywords:
                if keyword in text:
                    suggestion = keyword
                    break
        
        return suggestion
    
    def _extract_closing_price_date(self, rows: List[List[str]], text: str) -> Optional[str]:
        """提取收盘价日期"""
        date = None
        
        # 方法1: 从表格行中查找
        for row in rows:
            row_text = " ".join(row)
            
            # 查找包含"收盘价日期"的行
            if "收盘价日期" in row_text:
                # 在当前行或下一行查找日期
                search_rows = [row]
                row_index = rows.index(row)
                if row_index + 1 < len(rows):
                    search_rows.append(rows[row_index + 1])
                
                for search_row in search_rows:
                    for cell in search_row:
                        cell = cell.strip()
                        # 查找日期格式 YYYY-MM-DD
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cell)
                        if date_match:
                            date = date_match.group(1)
                            break
                
                if date:
                    break
        
        # 方法2: 从文本中直接提取
        if not date:
            date_patterns = [
                r'收盘价日期[：:]\s*(\d{4}-\d{2}-\d{2})',
                r'收盘价日期\s+(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})\s*收盘价日期',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    date = match.group(1)
                    break
        
        # 方法3: 查找所有日期，取第一个符合格式的
        if not date:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if date_match:
                date = date_match.group(1)
        
        return date


def main():
    """测试欧线解析器"""
    import json
    
    # 模拟测试数据（基于页面截图）
    test_rows = [
        ["欧线价格信号", "", "", "", "", ""],
        ["收盘价日期: 2025-11-21", "", "", "", "", ""],
        ["预测值", "偏离度", "当前值", "", "", ""],
        ["1569", "13%", "1773.9", "", "", ""],
        ["开空入场区间", "平空离场区间", "操作建议", "", "", ""],
        [">2275", "<1804", "平空", "", "", ""]
    ]
    
    parser = EuropeanLineParser()
    result = parser.parse_european_line_data(test_rows)
    
    print("=== 欧线数据解析结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

