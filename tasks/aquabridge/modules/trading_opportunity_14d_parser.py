#!/usr/bin/env python3
"""
14天后单边交易机会汇总数据解析器
专门用于解析14天后单边交易机会汇总页面的数据结构
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class TradingOpportunity14dParser:
    """14天后单边交易机会汇总数据解析器"""
    
    def __init__(self):
        self.parsed_data = {}
    
    def parse_trading_opportunity_14d_data(self, rows: List[List[str]]) -> Dict[str, Any]:
        """解析14天后单边交易机会汇总页面数据
        
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
                "page_name": "14天后单边交易机会汇总",
                "parsed_at": datetime.now().isoformat(),
                "data_source": "AquaBridge"
            },
            "date": self._extract_date(rows, text_data),
            "trading_opportunities": self._extract_trading_opportunities(rows, text_data)
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
    
    def _extract_trading_opportunities(self, rows: List[List[str]], text: str) -> List[Dict[str, Any]]:
        """提取交易机会数据
        
        每个交易机会包含：
        - 项目标识（C5, C10, P6, C3, P5, P3A, S5, S1C, S2, C14, S10等）
        - 建议交易方向（做多/做空）
        - 盈亏比（如 18.31: 1）
        """
        opportunities = []
        
        # 项目标识模式：字母+数字的组合，如 C5, C10, P6, P3A, S5, S1C, S2, C14, S10
        project_pattern = r'^([A-Z]\d+[A-Z]?)$'
        
        # 交易方向关键词
        direction_keywords = ['做多', '做空']
        
        # 盈亏比模式：支持多种格式
        # 格式1: "18.31: 1" (有空格，半角冒号)
        # 格式2: "18.31:1" (无空格，半角冒号)
        # 格式3: "18.31：1" (全角冒号)
        # 格式4: "18.31： 1" (全角冒号+空格)
        # 格式5: "18.31" (只有数字，可能冒号在另一个单元格)
        profit_loss_patterns = [
            r'(\d+\.\d+)\s*[：:]\s*1',      # 标准格式：18.31: 1 或 18.31： 1
            r'(\d+\.\d+)\s*[：:]1',        # 无空格格式：18.31:1 或 18.31：1
            r'(\d+\.\d+)\s*[：:]',         # 只有冒号：18.31: 或 18.31：
            r'(\d+\.\d+)(?:\s|$)',         # 只有数字（小数点格式）：18.31
            r'(\d+)\s*[：:]\s*1',          # 整数格式：18: 1
            r'(\d+)\s*[：:]1',              # 整数无空格格式：18:1
        ]
        
        # 遍历所有行，查找交易机会数据
        for i, row in enumerate(rows):
            # 过滤空单元格
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if not non_empty_cells:
                continue
            
            # 查找项目标识（通常在第一个非空单元格）
            project_id = None
            project_index = -1
            
            for idx, cell in enumerate(non_empty_cells):
                cell = cell.strip()
                # 检查是否是项目标识
                if re.match(project_pattern, cell):
                    project_id = cell
                    project_index = idx
                    break
            
            if not project_id:
                continue
            
            # 在同一行的其他单元格中查找交易方向和盈亏比
            trading_direction = None
            profit_loss_ratio = None
            
            # 从项目标识后面的单元格开始查找
            for idx in range(project_index + 1, len(non_empty_cells)):
                cell = non_empty_cells[idx].strip()
                
                # 查找交易方向
                if not trading_direction:
                    for keyword in direction_keywords:
                        if keyword in cell:
                            trading_direction = keyword
                            break
                
                # 查找盈亏比 - 尝试所有模式
                if not profit_loss_ratio:
                    for pattern in profit_loss_patterns:
                        match = re.search(pattern, cell)
                        if match:
                            profit_loss_ratio = match.group(1)
                            break
                
                # 如果都找到了，可以提前退出
                if trading_direction and profit_loss_ratio:
                    break
            
            # 如果当前行没有找全，检查下一行（某些表格可能跨行）
            if (not trading_direction or not profit_loss_ratio) and i + 1 < len(rows):
                next_row = rows[i + 1]
                next_non_empty = [cell.strip() for cell in next_row if cell.strip()]
                
                for cell in next_non_empty:
                    # 查找交易方向
                    if not trading_direction:
                        for keyword in direction_keywords:
                            if keyword in cell:
                                trading_direction = keyword
                                break
                    
                    # 查找盈亏比
                    if not profit_loss_ratio:
                        for pattern in profit_loss_patterns:
                            match = re.search(pattern, cell)
                            if match:
                                profit_loss_ratio = match.group(1)
                                break
                    
                    if trading_direction and profit_loss_ratio:
                        break
            
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
            # 重新扫描，使用更宽松的策略：逐单元格分析
            opportunities = []
            
            for i, row in enumerate(rows):
                # 过滤空单元格
                non_empty_cells = [cell.strip() for cell in row if cell.strip()]
                if not non_empty_cells:
                    continue
                
                # 查找项目标识（逐个单元格检查）
                project_id = None
                project_cell_index = -1
                
                for idx, cell in enumerate(non_empty_cells):
                    cell = cell.strip()
                    if re.match(project_pattern, cell):
                        project_id = cell
                        project_cell_index = idx
                        break
                
                if not project_id:
                    continue
                
                # 在同一行的其他单元格中查找交易方向和盈亏比
                trading_direction = None
                profit_loss_ratio = None
                
                # 检查项目标识所在单元格之后的所有单元格
                for idx in range(project_cell_index + 1, len(non_empty_cells)):
                    cell = non_empty_cells[idx].strip()
                    
                    # 查找交易方向
                    if not trading_direction:
                        for keyword in direction_keywords:
                            if keyword in cell:
                                trading_direction = keyword
                                break
                    
                    # 查找盈亏比 - 尝试所有模式
                    if not profit_loss_ratio:
                        for pattern in profit_loss_patterns:
                            match = re.search(pattern, cell)
                            if match:
                                profit_loss_ratio = match.group(1)
                                break
                    
                    # 如果都找到了，可以提前退出
                    if trading_direction and profit_loss_ratio:
                        break
                
                # 如果当前行没有找全，检查相邻行
                if (not trading_direction or not profit_loss_ratio) and i + 1 < len(rows):
                    next_row = rows[i + 1]
                    next_non_empty = [cell.strip() for cell in next_row if cell.strip()]
                    
                    for cell in next_non_empty:
                        # 查找交易方向
                        if not trading_direction:
                            for keyword in direction_keywords:
                                if keyword in cell:
                                    trading_direction = keyword
                                    break
                        
                        # 查找盈亏比
                        if not profit_loss_ratio:
                            for pattern in profit_loss_patterns:
                                match = re.search(pattern, cell)
                                if match:
                                    profit_loss_ratio = match.group(1)
                                    break
                        
                        if trading_direction and profit_loss_ratio:
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
        ["14天后单边交易机会汇总", "", "", ""],
        ["2025-11-26", "", "", ""],
        ["现货", "", "", ""],
        ["C5", "做多", "18.31: 1", ""],
        ["C10", "做多", "4.56: 1", ""],
        ["P6", "做多", "4.47: 1", ""],
        ["C3", "做多", "3.31: 1", ""],
        ["P5", "做空", "2.82: 1", ""],
        ["P3A", "做空", "2.05: 1", ""],
        ["S5", "做多", "1.15: 1", ""],
        ["S1C", "做多", "1.15: 1", ""],
        ["S2", "做多", "1.11: 1", ""],
        ["C14", "做多", "1.09: 1", ""],
        ["S10", "做多", "0.91: 1", ""]
    ]
    
    parser = TradingOpportunity14dParser()
    result = parser.parse_trading_opportunity_14d_data(test_rows)
    
    print("=== 14天后单边交易机会汇总数据解析结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

