"""
船舶油耗预测系统核心模块
Ship Fuel Consumption Prediction System Core Modules

这个包包含了船舶油耗预测系统的所有核心功能模块：
- data_analyzer: 数据分析模块
- cp_clause_definitions: CP条款定义和行业标准
- feature_engineering: 特征工程模块
- fuel_prediction_models: 预测模型核心
- model_validation: 模型验证模块

作者: 船舶油耗预测系统团队
版本: v1.0.0
日期: 2025-09-18
"""

__version__ = "1.0.0"
__author__ = "船舶油耗预测系统团队"
__email__ = "support@fuel-prediction.com"

# 导入核心类
from .data_analyzer import ShipFuelDataAnalyzer
from .cp_clause_definitions import CPClauseCalculator, ShipType, LoadCondition
from .feature_engineering import ShipFuelFeatureEngineer
from .fuel_prediction_models import MultiShipTypePredictor, ShipTypePredictor
from .model_validation import ModelValidator

__all__ = [
    'ShipFuelDataAnalyzer',
    'CPClauseCalculator',
    'ShipType',
    'LoadCondition',
    'ShipFuelFeatureEngineer',
    'MultiShipTypePredictor',
    'ShipTypePredictor',
    'ModelValidator'
]
