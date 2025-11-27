#!/usr/bin/env python3
"""
42天后单边交易机会汇总数据解析器
专门用于解析42天后单边交易机会汇总页面的数据结构
包含现货和期货两个部分，需要区分对待
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class TradingOpportunity42dParser:
    """42天后单边交易机会汇总数据解析器"""
    
    def __init__(self):
        self.parsed_data = {}
    
    def parse_trading_opportunity_42d_data(self, rows: List[List[str]]) -> Dict[str, Any]:
        """解析42天后单边交易机会汇总页面数据
        
        Args:
            rows: 表格行数据列表
            
        Returns:
            解析后的结构化数据字典，包含现货和期货两个部分
        """
        if not rows:
            return {}
        
        # 将表格数据转换为文本进行分析
        text_data = self._rows_to_text(rows)
        
        # 解析各个部分
        self.parsed_data = {
            "metadata": {
                "page_name": "42天后单边交易机会汇总",
                "parsed_at": datetime.now().isoformat(),
                "data_source": "AquaBridge"
            },
            "date": self._extract_date(rows, text_data),
            "spot_opportunities": self._extract_opportunities_by_section(rows, text_data, "现货"),
            "futures_opportunities": self._extract_opportunities_by_section(rows, text_data, "期货")
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
    
    def _extract_date(self, rows: List[List[str]], text: str) -> Optional[str]:
        """提取日期信息（如 2025-11-26）"""
        date = None
        
        # 方法1: 从表格行中查找日期
        for row in rows:
            for cell in row:
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
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if date_match:
                date = date_match.group(1)
        
        return date
    
    def _extract_opportunities_by_section(self, rows: List[List[str]], text: str, section_name: str) -> List[Dict[str, Any]]:
        """提取指定部分（现货或期货）的交易机会数据
        
        Args:
            rows: 表格行数据列表
            text: 文本数据
            section_name: 部分名称（"现货" 或 "期货"）
            
        Returns:
            交易机会列表
        """
        opportunities = []
        
        # 项目标识模式：字母+数字的组合，如 C5, C10, P6, P3A, S5, S1C, S2, C14, S10, C5TC, S4B等
        # 支持格式：C5, C5TC, S4B, P3A, P4TC+1, C5TC+1, C5+1等
        project_pattern = r'^([A-Z]\d+[A-Z]*[+\d]*|[A-Z]+\d+[A-Z]*[+\d]*)$'
        
        # 交易方向关键词
        direction_keywords = ['做多', '做空']
        
        # 盈亏比模式：支持多种格式
        # 格式1: "14: 1" (整数，有空格)
        # 格式2: "11.18: 1" (小数，有空格)
        # 格式3: "14:1" (整数，无空格)
        # 格式4: "11.18:1" (小数，无空格)
        profit_loss_patterns = [
            r'(\d+\.?\d+)\s*[：:]\s*1',      # 标准格式：14: 1 或 11.18: 1
            r'(\d+\.?\d+)\s*[：:]1',        # 无空格格式：14:1 或 11.18:1
        ]
        
        # 查找部分开始位置（"现货" 或 "期货"）
        section_start_index = -1
        section_end_index = len(rows)
        
        for i, row in enumerate(rows):
            # 将行转换为文本（处理多单元格情况）
            row_text = " ".join([cell.strip() for cell in row if cell.strip()])
            if section_name in row_text and len(row_text.strip()) <= 10:  # 确保是标题行
                section_start_index = i + 1  # 从下一行开始
                # 查找下一个部分或结束位置
                for j in range(i + 1, len(rows)):
                    next_row_text = " ".join([cell.strip() for cell in rows[j] if cell.strip()])
                    if "期货" in next_row_text and section_name == "现货" and len(next_row_text.strip()) <= 10:
                        section_end_index = j
                        break
                    elif "现货" in next_row_text and section_name == "期货" and len(next_row_text.strip()) <= 10:
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
            # 将行转换为文本（处理多单元格情况，但优先使用完整行文本）
            row_text = " ".join([cell.strip() for cell in row if cell.strip()])
            
            # 跳过空行和标题行
            if not row_text or section_name in row_text or len(row_text.strip()) < 2:
                continue
            
            # 查找项目标识（从完整行文本中）
            project_id = None
            
            # 扩展的项目标识列表（按长度排序，长的在前，避免短标识误匹配）
            all_project_ids = ['P4TC+1', 'C5TC+1', 'C5+1', 'C5TC', 'P4TC', 'S4B', 'P3A', 'S1C', 
                              'S15', 'S4A', 'S1B', 'P1A', 'C16', 'C10', 'S10', 'C14', 'C9', 'C8', 
                              'C5', 'P6', 'P4', 'C3', 'P5', 'P2', 'S5', 'P0', 'S8', 'S9', 'S2', 'S3']
            
            for pid in all_project_ids:
                # 使用单词边界确保精确匹配
                pid_pattern = rf'\b{re.escape(pid)}\b'
                if re.search(pid_pattern, row_text):
                    project_id = pid
                    break
            
            if not project_id:
                continue
            
            # 从行的完整文本中提取交易方向和盈亏比
            trading_direction = None
            profit_loss_ratio = None
            
            # 提取交易方向
            if '做多' in row_text:
                trading_direction = '做多'
            elif '做空' in row_text:
                trading_direction = '做空'
            
            # 提取盈亏比 - 尝试所有模式
            # 首先尝试匹配 "数字: 1" 或 "数字：1" 格式
            for pattern in profit_loss_patterns:
                match = re.search(pattern, row_text)
                if match:
                    profit_loss_ratio = match.group(1)
                    break
            
            # 如果没找到，尝试从单元格数据中提取（如果行数据已经是解析好的格式）
            if not profit_loss_ratio and len(row) >= 3:
                # 检查第三个单元格是否是盈亏比数字
                ratio_cell = row[2].strip() if len(row) > 2 else ''
                # 如果是纯数字或数字格式，直接使用
                if ratio_cell and re.match(r'^\d+\.?\d*$', ratio_cell):
                    profit_loss_ratio = ratio_cell
            
            # 如果找到了项目标识，记录这条交易机会
            if project_id:
                opportunity = {
                    "project_id": project_id,
                    "trading_direction": trading_direction,
                    "profit_loss_ratio": profit_loss_ratio
                }
                opportunities.append(opportunity)
        
        # 如果上面的方法没有找到足够的数据，尝试更宽松的匹配策略
        if len(opportunities) < 3:
            # 重新扫描，使用更宽松的策略：逐行分析，不依赖列位置
            opportunities = []
            
            for i, row in enumerate(search_rows):
                # 过滤空单元格
                non_empty_cells = [cell.strip() for cell in row if cell.strip()]
                if not non_empty_cells:
                    continue
                
                # 跳过包含部分名称的行
                row_text = " ".join(non_empty_cells)
                if section_name in row_text and len(non_empty_cells) <= 2:
                    continue
                
                # 查找项目标识
                project_match = re.search(project_pattern, row_text)
                if not project_match:
                    continue
                
                project_id = project_match.group(1)
                
                # 查找交易方向
                trading_direction = None
                for keyword in direction_keywords:
                    if keyword in row_text:
                        trading_direction = keyword
                        break
                
                # 查找盈亏比 - 尝试所有模式
                profit_loss_ratio = None
                for pattern in profit_loss_patterns:
                    match = re.search(pattern, row_text)
                    if match:
                        profit_loss_ratio = match.group(1)
                        break
                
                # 如果找到了项目标识，记录这条交易机会
                if project_id:
                    opportunity = {
                        "project_id": project_id,
                        "trading_direction": trading_direction,
                        "profit_loss_ratio": profit_loss_ratio
                    }
                    opportunities.append(opportunity)
        
        return opportunities


def main():
    """测试解析器"""
    import json
    
    # 模拟测试数据（基于页面截图）
    test_rows = [
        ["42天后单边交易机会汇总", "", "", ""],
        ["2025-11-26", "", "", ""],
        ["现货", "", "", ""],
        ["C5", "做多", "14: 1", ""],
        ["P6", "做多", "11.18: 1", ""],
        ["P4", "做多", "10.78: 1", ""],
        ["C5TC", "做多", "9.99: 1", ""],
        ["S4B", "做多", "9.38: 1", ""],
        ["C10", "做多", "5.07: 1", ""],
        ["S10", "做多", "4.41: 1", ""],
        ["C3", "做多", "3.43: 1", ""],
        ["P4TC", "做多", "2.58: 1", ""],
        ["P3A", "做空", "2.56: 1", ""],
        ["S15", "做多", "2.55: 1", ""],
        ["C14", "做空", "2.53: 1", ""],
        ["P5", "做空", "2.39: 1", ""],
        ["期货", "", "", ""],
        ["P2", "做多", "2.33: 1", ""],
        ["C9", "做多", "2.03: 1", ""],
        ["S5", "做多", "1.84: 1", ""],
        ["P0", "做多", "1.78: 1", ""]
    ]
    
    parser = TradingOpportunity42dParser()
    result = parser.parse_trading_opportunity_42d_data(test_rows)
    
    print("=== 42天后单边交易机会汇总数据解析结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

