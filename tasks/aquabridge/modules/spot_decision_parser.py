#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现货应用决策数据解析器（通用版）
支持 P3A、P5、P6 等所有现货应用决策页面，与 P4TC 区分开来
支持 14d 和 42d 版本
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class SpotDecisionParser:
    """现货应用决策数据解析器（通用版）"""
    
    def __init__(self):
        self.parsed_data = {}
    
    def parse_spot_decision_data(self, rows: List[List[str]], page_name: str = "") -> Dict[str, Any]:
        """解析现货应用决策页面数据，支持多种产品（P3A、P5、P6）和版本（14d、42d）"""
        if not rows:
            return {}
        
        # 将表格数据转换为文本进行分析
        text_data = self._rows_to_text(rows)
        
        # 检测产品类型（P3A、P5、P6、C3、C5等）
        product_type = self._detect_product_type(page_name, text_data)
        
        # 检测是14d还是42d版本
        # 注意：C3和C5可能没有明确的版本标识，需要更精确的检测
        is_14d = False
        is_42d = False
        
        # 优先检测明确的版本标识
        if "14天后" in page_name or "二周后" in text_data or "预测14天后" in text_data:
            is_14d = True
        elif "42天后" in page_name or "六周后" in text_data or "预测42天后" in text_data:
            is_42d = True
        else:
            # 如果没有明确的版本标识，检查是否有14d或42d的特征
            # 14d特征：档位区间、当前评估价格、二周后预测模型评价
            # 42d特征：盈亏比数据、六周后预测模型评价
            has_14d_features = "档位区间" in text_data or "当前评估价格" in text_data or "二周后预测模型评价" in text_data
            has_42d_features = "盈亏比" in text_data and ("42天后" in text_data or "六周后" in text_data or "预测模型评价" in text_data)
            
            # C3和C5默认使用42d结构（有盈亏比数据，没有TC模型评价）
            if product_type in ["C3", "C5"]:
                is_42d = True  # C3和C5默认使用42d结构
            elif has_14d_features and not has_42d_features:
                is_14d = True
            elif has_42d_features:
                is_42d = True
            else:
                # 默认使用42d结构
                is_42d = True
        
        # 解析各个部分
        self.parsed_data = {
            "metadata": {
                "page_name": page_name or "现货应用决策",
                "product_type": product_type,
                "version": "14d" if is_14d else "42d" if is_42d else "unknown",
                "parsed_at": datetime.now().isoformat(),
                "data_source": "AquaBridge"
            },
            "trading_recommendation": self._extract_trading_recommendation(text_data),
            "current_forecast": self._extract_current_forecast(text_data, is_14d),
            "positive_returns": self._extract_positive_returns(text_data, is_14d),
            "negative_returns": self._extract_negative_returns(text_data, is_14d),
        }
        
        # 根据版本和产品类型添加不同的数据部分
        # C3和C5可能没有TC模型评价，只有盈亏比数据
        if is_14d:
            # 14d版本特有的数据
            self.parsed_data[f"{product_type.lower()}_current_evaluation_price"] = self._extract_current_evaluation_price(text_data, product_type)
            # C3和C5可能没有TC模型评价
            tc_14d_eval = self._extract_tc_14d_model_evaluation(text_data, product_type)
            if tc_14d_eval and any(tc_14d_eval.values()):
                self.parsed_data[f"{product_type.lower()}tc_14d_model_evaluation"] = tc_14d_eval
        else:
            # 42d版本的数据（C3没有版本标识，默认使用42d结构）
            self.parsed_data[f"{product_type.lower()}_profit_loss_ratio"] = self._extract_profit_loss_ratio(text_data, product_type)
            # C3和C5可能没有TC模型评价
            tc_eval = self._extract_tc_model_evaluation(text_data, product_type)
            if tc_eval and any(tc_eval.values()):
                self.parsed_data[f"{product_type.lower()}tc_model_evaluation"] = tc_eval
        
        return self.parsed_data
    
    def _detect_product_type(self, page_name: str, text_data: str) -> str:
        """检测产品类型"""
        # 按优先级检测（C3和C5需要优先检测，避免被P3A、P5、P6误匹配）
        if "C3" in page_name or "C3" in text_data:
            return "C3"
        elif "C5" in page_name or "C5" in text_data:
            return "C5"
        elif "P3A" in page_name or "P3A" in text_data:
            return "P3A"
        elif "P5" in page_name or "P5" in text_data:
            return "P5"
        elif "P6" in page_name or "P6" in text_data:
            return "P6"
        elif "P4TC" in page_name or "P4TC" in text_data:
            return "P4TC"
        else:
            # 默认返回 P5（向后兼容）
            return "P5"
    
    def _rows_to_text(self, rows: List[List[str]]) -> str:
        """将表格行转换为文本"""
        text_lines = []
        for row in rows:
            # 过滤空单元格并连接
            non_empty_cells = [cell.strip() for cell in row if cell.strip()]
            if non_empty_cells:
                text_lines.append(" ".join(non_empty_cells))
        return "\n".join(text_lines)
    
    def _extract_trading_recommendation(self, text: str) -> Dict[str, Any]:
        """提取交易建议信息（支持做空胜率统计和做多胜率统计）"""
        recommendation = {
            "profit_loss_ratio": None,
            "recommended_direction": None,
            "direction_confidence": None,
            "statistics_type": None  # "做空胜率统计" 或 "做多胜率统计"
        }
        
        # 检测统计类型（做空或做多）
        if "做多胜率统计" in text:
            recommendation["statistics_type"] = "做多胜率统计"
        elif "做空胜率统计" in text:
            recommendation["statistics_type"] = "做空胜率统计"
        elif "做多" in text and "胜率" in text:
            recommendation["statistics_type"] = "做多胜率统计"
        elif "做空" in text and "胜率" in text:
            recommendation["statistics_type"] = "做空胜率统计"
        
        # 提取盈亏比 - 支持多种格式，包括∞（无限大）
        # 首先检查是否有∞符号（可能是"∞"、"infinity"、"Infinity"等）
        infinity_patterns = [
            r'盈亏比[：:]\s*∞',                      # 盈亏比：∞
            r'盈亏比[：:]\s*infinity',               # 盈亏比：infinity
            r'盈亏比[：:]\s*Infinity',               # 盈亏比：Infinity
            r'∞\s*盈亏比',                          # ∞ 盈亏比
            r'infinity\s*盈亏比',                   # infinity 盈亏比
        ]
        
        for pattern in infinity_patterns:
            infinity_match = re.search(pattern, text, re.IGNORECASE)
            if infinity_match:
                recommendation["profit_loss_ratio"] = "infinity"  # 使用字符串"infinity"表示无限大
                break
        
        # 如果没有找到∞，尝试匹配数字格式
        if recommendation["profit_loss_ratio"] is None:
            ratio_patterns = [
                r'盈亏比[：:]\s*(\d+\.?\d*)[：:]\s*1',  # 盈亏比：2.39：1
                r'盈亏比[：:]\s*(\d+\.?\d*):1',         # 盈亏比：2.39:1
                r'(\d+\.?\d*)[：:]\s*1',                # 2.39：1
                r'(\d+\.?\d*):1',                       # 2.39:1
            ]
            
            for pattern in ratio_patterns:
                ratio_match = re.search(pattern, text)
                if ratio_match:
                    recommendation["profit_loss_ratio"] = float(ratio_match.group(1))
                    break
        
        # 提取建议交易方向（优先检测做多，因为C3使用做多）
        if "做多" in text:
            recommendation["recommended_direction"] = "做多"
            recommendation["direction_confidence"] = "高"
        elif "做空" in text:
            recommendation["recommended_direction"] = "做空"
            recommendation["direction_confidence"] = "高"
        
        return recommendation
    
    def _extract_current_forecast(self, text: str, is_14d: bool = False) -> Dict[str, Any]:
        """提取当前预测信息"""
        forecast = {
            "date": None,
            "current_value": None,
            "comprehensive_spread_ratio": None,
            "comprehensive_spread_ratio_range": None,
            "gear_interval": None,  # 14d版本特有
            "forecast_date": None,
            "forecast_value": None,
            "probability": None
        }
        
        # 提取日期
        date_patterns = [
            r'日期[：:]\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                forecast["date"] = date_match.group(1)
                break
        
        # 提取当期值（支持小数，如C3的价格可能是24.74）
        current_value_patterns = [
            r'当期值[：:]\s*(\d+\.?\d*)',  # 支持小数
            r'当期值\s*(\d+\.?\d*)',
        ]
        for pattern in current_value_patterns:
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1)
                # 尝试转换为浮点数，如果是整数则保持整数
                try:
                    value_float = float(value_str)
                    forecast["current_value"] = value_float if '.' in value_str else int(value_float)
                except ValueError:
                    pass
                break
        
        # 提取综合价差比
        spread_ratio_patterns = [
            r'综合价差比[：:]\s*(-?\d+%)',
            r'综合价差比\s*(-?\d+%)',
        ]
        for pattern in spread_ratio_patterns:
            match = re.search(pattern, text)
            if match:
                forecast["comprehensive_spread_ratio"] = match.group(1)
                break
        
        # 提取综合价差比区间
        spread_range_patterns = [
            r'综合价差比区间[：:]\s*(-?\d+%)\s*-\s*(\d+%)',
            r'综合价差比区间\s*(-?\d+%)\s*-\s*(\d+%)',
        ]
        for pattern in spread_range_patterns:
            match = re.search(pattern, text)
            if match:
                forecast["comprehensive_spread_ratio_range"] = f"{match.group(1)} - {match.group(2)}"
                break
        
        # 提取档位区间（14d版本特有）
        if is_14d:
            gear_interval_patterns = [
                r'档位区间[：:]\s*(\d+)\s*~\s*(\d+)',
                r'档位区间\s*(\d+)\s*~\s*(\d+)',
                r'(\d+)\s*~\s*(\d+)',  # 通用格式
            ]
            for pattern in gear_interval_patterns:
                match = re.search(pattern, text)
                if match:
                    forecast["gear_interval"] = f"{match.group(1)} ~ {match.group(2)}"
                    break
        
        # 提取预测日期和预测值（支持小数）
        forecast_patterns = [
            r'(\d{4}-\d{2}-\d{2})预测值[：:]\s*(\d+\.?\d*)',  # 支持小数
            r'(\d{4}-\d{2}-\d{2})预测值\s*(\d+\.?\d*)',
        ]
        for pattern in forecast_patterns:
            match = re.search(pattern, text)
            if match:
                forecast["forecast_date"] = match.group(1)
                value_str = match.group(2)
                # 尝试转换为浮点数，如果是整数则保持整数
                try:
                    value_float = float(value_str)
                    forecast["forecast_value"] = value_float if '.' in value_str else int(value_float)
                except ValueError:
                    pass
                break
        
        # 提取出现概率
        # 支持多种格式：在全部交易日期中出现概率、在全部交易日期中出现等
        prob_patterns = [
            r'在全部交易日期中出现概率[：:]\s*(\d+)%',  # 在全部交易日期中出现概率：7%
            r'在全部交易日期中出现概率\s*(\d+)%',       # 在全部交易日期中出现概率 7%
            r'在全部交易日期中出现[：:]\s*(\d+)%',      # 在全部交易日期中出现：7%
            r'在全部交易日期中出现\s*(\d+)%',           # 在全部交易日期中出现 7%
            r'出现概率[：:]\s*(\d+)%',                  # 出现概率：7%
            r'出现概率\s*(\d+)%',                         # 出现概率 7%
        ]
        for pattern in prob_patterns:
            match = re.search(pattern, text)
            if match:
                forecast["probability"] = int(match.group(1))
                break
        
        return forecast
    
    def _extract_positive_returns(self, text: str, is_14d: bool = False) -> Dict[str, Any]:
        """提取正收益统计"""
        positive = {
            "final_positive_returns_percentage": None,
            "final_positive_returns_average": None,  # 14d可能是数值，42d可能是百分比
            "distribution": {},
            "statistics": {},
            "timing_distribution": {}
        }
        
        # 提取最终正收益占比和平均值
        # 14d版本：最终正收益平均值可能是数值（如1419），42d版本是百分比（如22%）
        # 支持两种格式：数值在前或标签在前
        final_percent_patterns = [
            r'(\d+)%\s+最终正收益占比',           # 100% 最终正收益占比
            r'最终正收益占比[：:]\s*(\d+)%',      # 最终正收益占比：100%
            r'最终正收益占比\s+(\d+)%',          # 最终正收益占比 100%
        ]
        for pattern in final_percent_patterns:
            final_percent_match = re.search(pattern, text)
            if final_percent_match:
                positive["final_positive_returns_percentage"] = int(final_percent_match.group(1))
                break
        
        # 尝试匹配百分比格式（42d版本）
        final_avg_percent_patterns = [
            r'(\d+)%\s+最终正收益平均值',         # 31% 最终正收益平均值
            r'最终正收益平均值[：:]\s*(\d+)%',    # 最终正收益平均值：31%
            r'最终正收益平均值\s+(\d+)%',        # 最终正收益平均值 31%
        ]
        for pattern in final_avg_percent_patterns:
            final_avg_percent_match = re.search(pattern, text)
            if final_avg_percent_match:
                positive["final_positive_returns_average"] = int(final_avg_percent_match.group(1))
                break
        
        # 如果百分比格式没有匹配到，尝试匹配数值格式（14d版本）
        if positive["final_positive_returns_average"] is None:
            final_avg_value_match = re.search(r'最终正收益平均值[：:]\s*(\d+)', text)
            if final_avg_value_match:
                positive["final_positive_returns_average"] = int(final_avg_value_match.group(1))
        
        # 提取分布情况
        distribution_patterns = [
            (r'正收益比例0~15%[：:]\s*(\d+)%', '0-15%'),
            (r'正收益比例15\.01~30%[：:]\s*(\d+)%', '15.01-30%'),
            (r'正收益比例30~60%[：:]\s*(\d+)%', '30-60%'),
            (r'正收益比例大于60%[：:]\s*(\d+)%', '>60%'),
        ]
        
        for pattern, key in distribution_patterns:
            match = re.search(pattern, text)
            if match:
                positive["distribution"][key] = int(match.group(1))
        
        # 提取收益统计
        stats_patterns = [
            (r'最大正收益平均值[：:]\s*(\d+)%', 'max_positive_returns_average'),
            (r'最大正收益最大值[：:]\s*(\d+)%', 'max_positive_returns_maximum'),
            (r'最大正收益出现时间平均值[：:]\s*(\d+)', 'max_positive_returns_avg_time'),
        ]
        
        for pattern, key in stats_patterns:
            match = re.search(pattern, text)
            if match:
                positive["statistics"][key] = int(match.group(1)) if '%' not in key else int(match.group(1))
        
        # 提取时间分布
        timing_patterns = [
            (r'0~14天[：:]\s*(\d+)%', '0-14_days'),
            (r'15~28天[：:]\s*(\d+)%', '15-28_days'),
            (r'29~42天[：:]\s*(\d+)%', '29-42_days'),
        ]
        
        for pattern, key in timing_patterns:
            match = re.search(pattern, text)
            if match:
                positive["timing_distribution"][key] = int(match.group(1))
        
        return positive
    
    def _extract_negative_returns(self, text: str, is_14d: bool = False) -> Dict[str, Any]:
        """提取负收益统计"""
        negative = {
            "final_negative_returns_percentage": None,
            "final_negative_returns_average": None,  # 14d可能是数值，42d可能是百分比
            "distribution": {},
            "statistics": {}
        }
        
        # 提取最终负收益比例和平均值
        final_percent_match = re.search(r'(\d+)%\s+最终负收益比例', text)
        if final_percent_match:
            negative["final_negative_returns_percentage"] = int(final_percent_match.group(1))
        
        # 尝试匹配百分比格式（42d版本）
        final_avg_percent_match = re.search(r'(-?\d+)%\s+最终负收益平均值', text)
        if final_avg_percent_match:
            negative["final_negative_returns_average"] = int(final_avg_percent_match.group(1))
        else:
            # 尝试匹配数值格式（14d版本）
            final_avg_value_match = re.search(r'最终负收益平均值[：:]\s*(-?\d+)', text)
            if final_avg_value_match:
                negative["final_negative_returns_average"] = int(final_avg_value_match.group(1))
        
        # 提取分布情况
        distribution_patterns = [
            (r'负收益比例0~15%[：:]\s*(\d+)%', '0-15%'),
            (r'负收益比例15\.01~30%[：:]\s*(\d+)%', '15.01-30%'),
            (r'负收益比例30~60%[：:]\s*(\d+)%', '30-60%'),
            (r'负收益比例小于60%[：:]\s*(\d+)%', '<60%'),
        ]
        
        for pattern, key in distribution_patterns:
            match = re.search(pattern, text)
            if match:
                negative["distribution"][key] = int(match.group(1))
        
        # 提取收益统计
        stats_patterns = [
            (r'最小负收益平均值[：:]\s*(-?\d+)%', 'min_negative_returns_average'),
            (r'最小负收益最小值[：:]\s*(-?\d+)%', 'min_negative_returns_minimum'),
        ]
        
        for pattern, key in stats_patterns:
            match = re.search(pattern, text)
            if match:
                negative["statistics"][key] = int(match.group(1))
        
        return negative
    
    def _extract_profit_loss_ratio(self, text: str, product_type: str) -> Dict[str, Any]:
        """提取盈亏比数据（42d版本）"""
        profit_loss_data = {
            "current_price": None,
            "evaluated_price": None,
            "price_difference_ratio": None,
            "profit_ratio_42d": None,
            "profit_average_42d": None,
            "loss_ratio_42d": None,
            "loss_average_42d": None,
            "max_profit_timing_distribution": {},
            "max_risk_average": None,
            "max_risk_extreme": None,
            "max_risk_timing_distribution": {}
        }
        
        # 提取当前价格（支持小数，如C3的价格可能是24.74）
        # 支持格式：当前价格/元每吨 24.74 或 当前价格/元每吨：24.74
        current_price_patterns = [
            r'当前价格/元每吨[：:]\s*(\d+\.?\d*)',  # 有冒号
            r'当前价格/元每吨\s+(\d+\.?\d*)',  # 没有冒号，用空格分隔
            r'当前价格/元每吨\s*(\d+\.?\d*)',  # 没有冒号，可能有空格
        ]
        for pattern in current_price_patterns:
            current_price_match = re.search(pattern, text)
            if current_price_match:
                price_str = current_price_match.group(1)
                # 尝试转换为浮点数，如果是整数则保持整数
                try:
                    price_float = float(price_str)
                    profit_loss_data["current_price"] = price_float if '.' in price_str else int(price_float)
                except ValueError:
                    pass
                break
        
        # 提取评估价格（支持小数）
        # 支持格式：评估价格/元每吨 24.25 或 评估价格/元每吨：24.25
        evaluated_price_patterns = [
            r'评估价格/元每吨[：:]\s*(\d+\.?\d*)',  # 有冒号
            r'评估价格/元每吨\s+(\d+\.?\d*)',  # 没有冒号，用空格分隔
            r'评估价格/元每吨\s*(\d+\.?\d*)',  # 没有冒号，可能有空格
        ]
        for pattern in evaluated_price_patterns:
            evaluated_price_match = re.search(pattern, text)
            if evaluated_price_match:
                price_str = evaluated_price_match.group(1)
                # 尝试转换为浮点数，如果是整数则保持整数
                try:
                    price_float = float(price_str)
                    profit_loss_data["evaluated_price"] = price_float if '.' in price_str else int(price_float)
                except ValueError:
                    pass
                break
        
        # 提取价差比（支持有冒号和没有冒号的情况）
        # 优先提取盈亏比部分的价差比（在"盈亏比"或产品名称之后）
        # 例如：C3盈亏比 ... 价差比 -2%
        # 方法1：查找所有价差比，取最后一个（通常是盈亏比部分的，在综合价差比之后）
        all_price_diffs = re.findall(r'价差比\s+(-?\d+%)', text)
        if all_price_diffs:
            # 如果有多个价差比，取最后一个（通常是盈亏比部分的）
            profit_loss_data["price_difference_ratio"] = all_price_diffs[-1]
        else:
            # 方法2：尝试在盈亏比部分查找（使用DOTALL模式）
            profit_loss_section_pattern = r'(?:{}盈亏比|盈亏比).*?价差比\s+(-?\d+%)'.format(product_type)
            profit_loss_match = re.search(profit_loss_section_pattern, text, re.DOTALL)
            if profit_loss_match:
                profit_loss_data["price_difference_ratio"] = profit_loss_match.group(1)
            else:
                # 方法3：通用格式（有冒号）
                price_diff_patterns = [
                    r'价差比[：:]\s*(-?\d+%)',
                    r'价差比\s+(-?\d+%)',  # 没有冒号
                ]
                for pattern in price_diff_patterns:
                    price_diff_match = re.search(pattern, text)
                    if price_diff_match:
                        profit_loss_data["price_difference_ratio"] = price_diff_match.group(1)
                        break
        
        # 提取42天后盈利比例和收益均值（支持有冒号和没有冒号的情况）
        profit_ratio_patterns = [
            r'42天后盈利比例[：:]\s*(\d+)%',
            r'42天后盈利比例\s*(\d+)%',  # 没有冒号
        ]
        for pattern in profit_ratio_patterns:
            profit_ratio_match = re.search(pattern, text)
            if profit_ratio_match:
                profit_loss_data["profit_ratio_42d"] = int(profit_ratio_match.group(1))
                break
        
        profit_avg_patterns = [
            r'收益均值[：:]\s*(\d+)%',
            r'收益均值\s*(\d+)%',  # 没有冒号
        ]
        for pattern in profit_avg_patterns:
            profit_avg_match = re.search(pattern, text)
            if profit_avg_match:
                profit_loss_data["profit_average_42d"] = int(profit_avg_match.group(1))
                break
        
        # 提取42天后亏损比例和亏损均值（支持有冒号和没有冒号的情况）
        loss_ratio_patterns = [
            r'42天后亏损比例[：:]\s*(\d+)%',
            r'42天后亏损比例\s*(\d+)%',  # 没有冒号
        ]
        for pattern in loss_ratio_patterns:
            loss_ratio_match = re.search(pattern, text)
            if loss_ratio_match:
                profit_loss_data["loss_ratio_42d"] = int(loss_ratio_match.group(1))
                break
        
        loss_avg_patterns = [
            r'亏损均值/元每吨[：:]\s*(\d+)%',
            r'亏损均值/元每吨\s*(\d+)%',  # 没有冒号
            r'亏损均值[：:]\s*(\d+)%',  # 没有/元每吨
            r'亏损均值\s*(\d+)%',  # 没有冒号和/元每吨
        ]
        for pattern in loss_avg_patterns:
            loss_avg_match = re.search(pattern, text)
            if loss_avg_match:
                profit_loss_data["loss_average_42d"] = int(loss_avg_match.group(1))
                break
        
        # 提取最大收益时间分布（支持多种格式）
        # 为每个时间段单独匹配，确保都能提取到
        timing_patterns_0_14 = [
            r'0~14天[：:]\s*(\d+)%',
            r'0~14天\s+(\d+)%',  # 没有冒号
        ]
        for pattern in timing_patterns_0_14:
            match = re.search(pattern, text)
            if match:
                profit_loss_data["max_profit_timing_distribution"]['0-14_days'] = int(match.group(1))
                break
        
        timing_patterns_15_28 = [
            r'15天~28天[：:]\s*(\d+)%',  # 有"天"字
            r'15天~28天\s+(\d+)%',  # 有"天"字，没有冒号
            r'15~28天[：:]\s*(\d+)%',
            r'15~28天\s+(\d+)%',  # 没有冒号
        ]
        for pattern in timing_patterns_15_28:
            match = re.search(pattern, text)
            if match:
                profit_loss_data["max_profit_timing_distribution"]['15-28_days'] = int(match.group(1))
                break
        
        timing_patterns_29_42 = [
            r'29天~42天[：:]\s*(\d+)%',  # 有"天"字
            r'29天~42天\s+(\d+)%',  # 有"天"字，没有冒号
            r'29~42天[：:]\s*(\d+)%',
            r'29~42天\s+(\d+)%',  # 没有冒号
        ]
        for pattern in timing_patterns_29_42:
            match = re.search(pattern, text)
            if match:
                profit_loss_data["max_profit_timing_distribution"]['29-42_days'] = int(match.group(1))
                break
        
        # 提取最大风险均值（支持有冒号和没有冒号）
        max_risk_avg_patterns = [
            r'最大风险均值/元每吨[：:]\s*(-?\d+%)',
            r'最大风险均值/元每吨\s+(-?\d+%)',  # 没有冒号
        ]
        for pattern in max_risk_avg_patterns:
            max_risk_avg_match = re.search(pattern, text)
            if max_risk_avg_match:
                profit_loss_data["max_risk_average"] = max_risk_avg_match.group(1)
                break
        
        # 提取最大风险极值（支持有冒号和没有冒号）
        max_risk_extreme_patterns = [
            r'最大风险极值/元每吨[：:]\s*(-?\d+%)',
            r'最大风险极值/元每吨\s+(-?\d+%)',  # 没有冒号
        ]
        for pattern in max_risk_extreme_patterns:
            max_risk_extreme_match = re.search(pattern, text)
            if max_risk_extreme_match:
                profit_loss_data["max_risk_extreme"] = max_risk_extreme_match.group(1)
                break
        
        # 提取最大风险时间分布（支持多种格式）
        # 需要在"最大风险时间"部分之后查找，避免匹配到最大收益时间分布的值
        # 先找到"最大风险时间"的位置
        risk_timing_section_match = re.search(r'最大风险时间.*?出现概率', text, re.DOTALL)
        if risk_timing_section_match:
            # 只在"最大风险时间"部分之后查找
            risk_section_text = text[risk_timing_section_match.end():]
        else:
            # 如果找不到"最大风险时间"部分，尝试在"最大风险极值"之后查找
            risk_section_match = re.search(r'最大风险极值.*?', text, re.DOTALL)
            if risk_section_match:
                risk_section_text = text[risk_section_match.end():]
            else:
                # 如果都找不到，使用全文（向后兼容）
                risk_section_text = text
        
        # 为每个时间段单独匹配，确保都能提取到
        risk_timing_patterns_0_14 = [
            r'0~14天[：:]\s*(\d+)%',
            r'0~14天\s+(\d+)%',  # 没有冒号
        ]
        for pattern in risk_timing_patterns_0_14:
            match = re.search(pattern, risk_section_text)
            if match:
                profit_loss_data["max_risk_timing_distribution"]['0-14_days'] = int(match.group(1))
                break
        
        risk_timing_patterns_15_28 = [
            r'15天~28天[：:]\s*(\d+)%',  # 有"天"字
            r'15天~28天\s+(\d+)%',  # 有"天"字，没有冒号
            r'15~28天[：:]\s*(\d+)%',
            r'15~28天\s+(\d+)%',  # 没有冒号
        ]
        for pattern in risk_timing_patterns_15_28:
            match = re.search(pattern, risk_section_text)
            if match:
                profit_loss_data["max_risk_timing_distribution"]['15-28_days'] = int(match.group(1))
                break
        
        risk_timing_patterns_29_42 = [
            r'29天~42天[：:]\s*(\d+)%',  # 有"天"字
            r'29天~42天\s+(\d+)%',  # 有"天"字，没有冒号
            r'29~42天[：:]\s*(\d+)%',
            r'29~42天\s+(\d+)%',  # 没有冒号
        ]
        for pattern in risk_timing_patterns_29_42:
            match = re.search(pattern, risk_section_text)
            if match:
                profit_loss_data["max_risk_timing_distribution"]['29-42_days'] = int(match.group(1))
                break
        
        return profit_loss_data
    
    def _extract_current_evaluation_price(self, text: str, product_type: str) -> Dict[str, Any]:
        """提取当前评估价格（14d版本特有）"""
        evaluation_price = {
            "date": None,
            "current_price": None,
            "evaluated_price": None,
            "price_difference_ratio": None
        }
        
        # 提取日期
        date_match = re.search(r'日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            evaluation_price["date"] = date_match.group(1)
        
        # 提取当前价格（支持小数）
        current_price_patterns = [
            r'当前价格/元每吨[：:]\s*(\d+\.?\d*)',  # 支持小数
            r'当前价格/元每吨\s*(\d+\.?\d*)',
        ]
        for pattern in current_price_patterns:
            current_price_match = re.search(pattern, text)
            if current_price_match:
                price_str = current_price_match.group(1)
                try:
                    price_float = float(price_str)
                    evaluation_price["current_price"] = price_float if '.' in price_str else int(price_float)
                except ValueError:
                    pass
                break
        
        # 提取评估价格（支持小数）
        evaluated_price_patterns = [
            r'评估价格/元每吨[：:]\s*(\d+\.?\d*)',  # 支持小数
            r'评估价格/元每吨\s*(\d+\.?\d*)',
        ]
        for pattern in evaluated_price_patterns:
            evaluated_price_match = re.search(pattern, text)
            if evaluated_price_match:
                price_str = evaluated_price_match.group(1)
                try:
                    price_float = float(price_str)
                    evaluation_price["evaluated_price"] = price_float if '.' in price_str else int(price_float)
                except ValueError:
                    pass
                break
        
        # 提取价差比
        ratio_match = re.search(r'价差比[：:]\s*(-?\d+%)', text)
        if ratio_match:
            evaluation_price["price_difference_ratio"] = ratio_match.group(1)
        
        return evaluation_price
    
    def _extract_tc_14d_model_evaluation(self, text: str, product_type: str) -> Dict[str, Any]:
        """提取TC二周后预测模型评价数据（14d版本特有）"""
        evaluation = {
            "date": None,
            "current_price": None,
            "forecast_14day_price_difference": None,
            "forecast_14day_price": None,
            "price_difference_ratio": None,
            "evaluation_ranges": []
        }
        
        # 提取日期
        date_match = re.search(r'日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            evaluation["date"] = date_match.group(1)
        
        # 提取当前价格
        current_price_match = re.search(r'当前价格/元每吨[：:]\s*(\d+)', text)
        if current_price_match:
            evaluation["current_price"] = int(current_price_match.group(1))
        
        # 提取预测14天后价差
        price_diff_match = re.search(r'预测14天后价差/元每吨[：:]\s*(-?\d+)', text)
        if price_diff_match:
            evaluation["forecast_14day_price_difference"] = int(price_diff_match.group(1))
        
        # 提取预测14天后价格
        forecast_price_match = re.search(r'预测14天后价格/元每吨[：:]\s*(\d+)', text)
        if forecast_price_match:
            evaluation["forecast_14day_price"] = int(forecast_price_match.group(1))
        
        # 提取价差比
        ratio_match = re.search(r'价差比[：:]\s*(-?\d+%)', text)
        if ratio_match:
            evaluation["price_difference_ratio"] = ratio_match.group(1)
        
        # 提取区间评价数据
        range_patterns = [
            (r'<-5000\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '<-5000'),
            (r'-5000\s+~?\s+-2500\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '-5000~-2500'),
            (r'-2500\s+~?\s+0\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '-2500~0'),
            (r'0\s+~?\s+2500\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '0~2500'),
            (r'2500\s+~?\s+5000\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '2500~5000'),
            (r'>=5000\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '>=5000')
        ]
        
        for pattern, range_name in range_patterns:
            match = re.search(pattern, text)
            if match:
                evaluation["evaluation_ranges"].append({
                    "range": range_name,
                    "historical_accuracy_rate": float(match.group(1)),
                    "historical_actual_value": int(match.group(2)),
                    "historical_fit_value": int(match.group(3))
                })
        
        return evaluation
    
    def _extract_tc_model_evaluation(self, text: str, product_type: str) -> Dict[str, Any]:
        """提取TC六周后预测模型评价数据（42d版本）"""
        evaluation = {
            "date": None,
            "current_price": None,
            "forecast_42day_price_difference": None,
            "forecast_42day_price": None,
            "price_difference_ratio": None,
            "evaluation_ranges": []
        }
        
        # 提取日期
        date_match = re.search(r'日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            evaluation["date"] = date_match.group(1)
        
        # 提取当前价格
        current_price_match = re.search(r'当前价格/元每吨[：:]\s*(\d+)', text)
        if current_price_match:
            evaluation["current_price"] = int(current_price_match.group(1))
        
        # 提取预测42天后价差
        price_diff_match = re.search(r'预测42天后价差/元每吨[：:]\s*(-?\d+)', text)
        if price_diff_match:
            evaluation["forecast_42day_price_difference"] = int(price_diff_match.group(1))
        
        # 提取预测42天后价格
        forecast_price_match = re.search(r'预测42天后价格/元每吨[：:]\s*(\d+)', text)
        if forecast_price_match:
            evaluation["forecast_42day_price"] = int(forecast_price_match.group(1))
        
        # 提取价差比
        ratio_match = re.search(r'价差比[：:]\s*(-?\d+%)', text)
        if ratio_match:
            evaluation["price_difference_ratio"] = ratio_match.group(1)
        
        # 提取区间评价数据
        range_patterns = [
            (r'<-5000\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '<-5000'),
            (r'-5000\s+~?\s+-2500\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '-5000~-2500'),
            (r'-2500\s+~?\s+0\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '-2500~0'),
            (r'0\s+~?\s+2500\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '0~2500'),
            (r'2500\s+~?\s+5000\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '2500~5000'),
            (r'>=5000\s+(\d+\.?\d*)%\s+(-?\d+)\s+(-?\d+)', '>=5000')
        ]
        
        for pattern, range_name in range_patterns:
            match = re.search(pattern, text)
            if match:
                evaluation["evaluation_ranges"].append({
                    "range": range_name,
                    "historical_accuracy_rate": float(match.group(1)),
                    "historical_actual_value": int(match.group(2)),
                    "historical_fit_value": int(match.group(3))
                })
        
        return evaluation

