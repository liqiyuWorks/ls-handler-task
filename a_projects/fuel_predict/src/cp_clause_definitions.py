#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
航运CP条款定义和行业标准模块
Charter Party Clause Definitions and Industry Standards

基于国际航运惯例和CP条款的定义，为油耗预测提供行业标准参考

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np

class ShipType(Enum):
    """船舶类型枚举"""
    BULK_CARRIER = "BULK CARRIER"
    CONTAINER_SHIP = "CONTAINER SHIP"
    TANKER = "TANKER"
    GENERAL_CARGO = "General Cargo Ship"
    OPEN_HATCH_CARGO = "OPEN HATCH CARGO SHIP"
    RO_RO_CARGO = "RO-RO CARGO SHIP"
    VEHICLE_CARRIER = "VEHICLE CARRIER"
    CHEMICAL_TANKER = "CHEMICAL TANKER"
    OIL_TANKER = "OIL TANKER"

class LoadCondition(Enum):
    """载重状态枚举"""
    LADEN = "Laden"  # 满载
    BALLAST = "Ballast"  # 压载
    PART_LADEN = "Part Laden"  # 部分载货

class ReportType(Enum):
    """报告类型枚举"""
    NOON = "NOON"  # 正午报告
    COSP = "COSP"  # 开始海上航行
    EOSP = "EOSP"  # 结束海上航行
    DEPARTURE = "DEPARTURE"  # 离港
    ARRIVAL = "ARRIVAL"  # 到港

@dataclass
class CPClauseStandards:
    """CP条款标准定义"""
    
    # 速度标准 (knots)
    speed_standards: Dict[ShipType, Dict[LoadCondition, Tuple[float, float]]] = None
    
    # 油耗标准 (MT/day)
    consumption_standards: Dict[ShipType, Dict[LoadCondition, Dict[str, float]]] = None
    
    # 天气条件修正系数
    weather_correction_factors: Dict[str, float] = None
    
    # 海况修正系数
    sea_condition_factors: Dict[str, float] = None
    
    def __post_init__(self):
        """初始化标准值"""
        self._init_speed_standards()
        self._init_consumption_standards()
        self._init_weather_factors()
        self._init_sea_condition_factors()
    
    def _init_speed_standards(self):
        """初始化速度标准"""
        self.speed_standards = {
            ShipType.BULK_CARRIER: {
                LoadCondition.LADEN: (12.0, 14.5),  # (最小, 最大)
                LoadCondition.BALLAST: (13.0, 15.5)
            },
            ShipType.CONTAINER_SHIP: {
                LoadCondition.LADEN: (18.0, 24.0),
                LoadCondition.BALLAST: (19.0, 25.0)
            },
            ShipType.TANKER: {
                LoadCondition.LADEN: (13.0, 15.5),
                LoadCondition.BALLAST: (14.0, 16.5)
            },
            ShipType.GENERAL_CARGO: {
                LoadCondition.LADEN: (11.0, 14.0),
                LoadCondition.BALLAST: (12.0, 15.0)
            },
            ShipType.OPEN_HATCH_CARGO: {
                LoadCondition.LADEN: (12.5, 15.0),
                LoadCondition.BALLAST: (13.5, 16.0)
            }
        }
    
    def _init_consumption_standards(self):
        """初始化油耗标准"""
        self.consumption_standards = {
            ShipType.BULK_CARRIER: {
                LoadCondition.LADEN: {
                    "IFO": 25.0,  # 重油 MT/day
                    "MDO": 1.5,   # 轻油 MT/day
                    "total": 26.5
                },
                LoadCondition.BALLAST: {
                    "IFO": 22.0,
                    "MDO": 1.2,
                    "total": 23.2
                }
            },
            ShipType.CONTAINER_SHIP: {
                LoadCondition.LADEN: {
                    "IFO": 180.0,
                    "MDO": 8.0,
                    "total": 188.0
                },
                LoadCondition.BALLAST: {
                    "IFO": 160.0,
                    "MDO": 7.0,
                    "total": 167.0
                }
            },
            ShipType.TANKER: {
                LoadCondition.LADEN: {
                    "IFO": 35.0,
                    "MDO": 2.0,
                    "total": 37.0
                },
                LoadCondition.BALLAST: {
                    "IFO": 30.0,
                    "MDO": 1.8,
                    "total": 31.8
                }
            },
            ShipType.GENERAL_CARGO: {
                LoadCondition.LADEN: {
                    "IFO": 15.0,
                    "MDO": 1.0,
                    "total": 16.0
                },
                LoadCondition.BALLAST: {
                    "IFO": 13.0,
                    "MDO": 0.8,
                    "total": 13.8
                }
            }
        }
    
    def _init_weather_factors(self):
        """初始化天气修正系数"""
        self.weather_correction_factors = {
            "calm": 1.0,      # 风平浪静
            "light": 1.05,    # 轻风
            "moderate": 1.15, # 中等风力
            "strong": 1.25,   # 强风
            "gale": 1.40,     # 大风
            "storm": 1.60     # 风暴
        }
    
    def _init_sea_condition_factors(self):
        """初始化海况修正系数"""
        self.sea_condition_factors = {
            "calm": 1.0,      # 平静
            "slight": 1.03,   # 轻浪
            "moderate": 1.08, # 中浪
            "rough": 1.18,    # 大浪
            "very_rough": 1.30, # 巨浪
            "high": 1.45      # 狂浪
        }

class IndustryStandards:
    """航运行业标准"""
    
    @staticmethod
    def get_dwt_categories() -> Dict[str, Tuple[float, float]]:
        """获取载重吨位分类标准"""
        return {
            "Handysize": (10000, 40000),
            "Handymax": (40000, 60000),
            "Panamax": (60000, 80000),
            "Capesize": (80000, 200000),
            "VLBC": (200000, 400000),  # Very Large Bulk Carrier
            "ULBC": (400000, float('inf'))  # Ultra Large Bulk Carrier
        }
    
    @staticmethod
    def get_container_ship_categories() -> Dict[str, Tuple[int, int]]:
        """获取集装箱船分类标准 (TEU)"""
        return {
            "Feeder": (0, 1000),
            "Small_Feeder": (1000, 3000),
            "Handy": (3000, 8000),
            "Sub_Panamax": (8000, 10000),
            "Panamax": (10000, 14000),
            "Post_Panamax": (14000, 18000),
            "ULCV": (18000, float('inf'))  # Ultra Large Container Vessel
        }
    
    @staticmethod
    def get_tanker_categories() -> Dict[str, Tuple[float, float]]:
        """获取油轮分类标准 (DWT)"""
        return {
            "Small_Tanker": (0, 25000),
            "MR": (25000, 55000),      # Medium Range
            "LR1": (55000, 80000),     # Long Range 1
            "LR2": (80000, 120000),    # Long Range 2
            "VLCC": (200000, 320000),  # Very Large Crude Carrier
            "ULCC": (320000, float('inf'))  # Ultra Large Crude Carrier
        }
    
    @staticmethod
    def calculate_admiralty_coefficient(speed: float, power: float, displacement: float) -> float:
        """
        计算海军系数 (Admiralty Coefficient)
        AC = (Displacement^(2/3) × Speed^3) / Power
        
        Args:
            speed: 船舶速度 (knots)
            power: 主机功率 (kW)
            displacement: 排水量 (tons)
            
        Returns:
            海军系数
        """
        if power <= 0 or displacement <= 0:
            return 0
        
        return (displacement**(2/3) * speed**3) / power
    
    @staticmethod
    def calculate_fuel_efficiency_index(fuel_consumption: float, cargo_capacity: float, distance: float) -> float:
        """
        计算燃料效率指数
        FEI = Fuel Consumption / (Cargo Capacity × Distance)
        
        Args:
            fuel_consumption: 燃料消耗 (MT)
            cargo_capacity: 载货能力 (tons)
            distance: 航行距离 (nm)
            
        Returns:
            燃料效率指数 (MT/ton/nm)
        """
        if cargo_capacity <= 0 or distance <= 0:
            return float('inf')
        
        return fuel_consumption / (cargo_capacity * distance)

class CPClauseCalculator:
    """CP条款计算器"""
    
    def __init__(self):
        self.standards = CPClauseStandards()
    
    def calculate_warranted_speed(self, ship_type: ShipType, load_condition: LoadCondition, 
                                 dwt: float, weather_condition: str = "moderate") -> float:
        """
        计算保证航速
        
        Args:
            ship_type: 船舶类型
            load_condition: 载重状态
            dwt: 载重吨位
            weather_condition: 天气条件
            
        Returns:
            保证航速 (knots)
        """
        if ship_type not in self.standards.speed_standards:
            return 12.0  # 默认值
        
        speed_range = self.standards.speed_standards[ship_type][load_condition]
        base_speed = (speed_range[0] + speed_range[1]) / 2
        
        # 根据船舶大小调整
        size_factor = self._get_size_factor(ship_type, dwt)
        weather_factor = self.standards.weather_correction_factors.get(weather_condition, 1.15)
        
        warranted_speed = base_speed * size_factor / weather_factor
        
        return round(warranted_speed, 1)
    
    def calculate_warranted_consumption(self, ship_type: ShipType, load_condition: LoadCondition,
                                      dwt: float, speed: float) -> Dict[str, float]:
        """
        计算保证油耗
        
        Args:
            ship_type: 船舶类型
            load_condition: 载重状态
            dwt: 载重吨位
            speed: 航行速度
            
        Returns:
            保证油耗字典 (MT/day)
        """
        if ship_type not in self.standards.consumption_standards:
            return {"IFO": 20.0, "MDO": 1.0, "total": 21.0}
        
        base_consumption = self.standards.consumption_standards[ship_type][load_condition]
        
        # 根据船舶大小和速度调整
        size_factor = self._get_size_factor(ship_type, dwt)
        speed_factor = self._get_speed_factor(speed)
        
        warranted_consumption = {
            "IFO": base_consumption["IFO"] * size_factor * speed_factor,
            "MDO": base_consumption["MDO"] * size_factor * speed_factor,
        }
        warranted_consumption["total"] = warranted_consumption["IFO"] + warranted_consumption["MDO"]
        
        return {k: round(v, 2) for k, v in warranted_consumption.items()}
    
    def _get_size_factor(self, ship_type: ShipType, dwt: float) -> float:
        """根据船舶大小计算修正系数"""
        if ship_type == ShipType.BULK_CARRIER:
            if dwt < 40000:
                return 0.8
            elif dwt < 80000:
                return 1.0
            else:
                return 1.2
        elif ship_type == ShipType.CONTAINER_SHIP:
            if dwt < 50000:
                return 0.7
            elif dwt < 100000:
                return 1.0
            else:
                return 1.4
        else:
            return 1.0
    
    def _get_speed_factor(self, speed: float) -> float:
        """根据速度计算油耗修正系数"""
        # 油耗与速度的三次方关系
        base_speed = 12.0
        return (speed / base_speed) ** 3
    
    def calculate_performance_deviation(self, actual_speed: float, actual_consumption: float,
                                      warranted_speed: float, warranted_consumption: float) -> Dict[str, float]:
        """
        计算性能偏差
        
        Args:
            actual_speed: 实际航速
            actual_consumption: 实际油耗
            warranted_speed: 保证航速
            warranted_consumption: 保证油耗
            
        Returns:
            性能偏差字典
        """
        speed_deviation = ((actual_speed - warranted_speed) / warranted_speed) * 100
        consumption_deviation = ((actual_consumption - warranted_consumption) / warranted_consumption) * 100
        
        return {
            "speed_deviation_percent": round(speed_deviation, 2),
            "consumption_deviation_percent": round(consumption_deviation, 2),
            "performance_index": round(100 - abs(speed_deviation) - abs(consumption_deviation), 2)
        }

def main():
    """主函数示例"""
    # 创建CP条款计算器
    calculator = CPClauseCalculator()
    
    # 示例计算
    ship_type = ShipType.BULK_CARRIER
    load_condition = LoadCondition.LADEN
    dwt = 75000
    
    # 计算保证航速
    warranted_speed = calculator.calculate_warranted_speed(
        ship_type, load_condition, dwt, "moderate"
    )
    print(f"保证航速: {warranted_speed} knots")
    
    # 计算保证油耗
    warranted_consumption = calculator.calculate_warranted_consumption(
        ship_type, load_condition, dwt, warranted_speed
    )
    print(f"保证油耗: {warranted_consumption}")
    
    # 计算性能偏差
    actual_speed = 12.5
    actual_consumption = 28.5
    deviation = calculator.calculate_performance_deviation(
        actual_speed, actual_consumption["total"],
        warranted_speed, warranted_consumption["total"]
    )
    print(f"性能偏差: {deviation}")
    
    # 显示行业标准
    print("\n=== 行业标准 ===")
    dwt_categories = IndustryStandards.get_dwt_categories()
    print("散货船载重吨位分类:")
    for category, (min_dwt, max_dwt) in dwt_categories.items():
        print(f"  {category}: {min_dwt:,} - {max_dwt:,} DWT")

if __name__ == "__main__":
    main()
