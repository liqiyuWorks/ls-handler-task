#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型加载器 - 解决pickle模块导入问题
Model Loader - Fix pickle module import issues

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pickle
import sys
import os
from typing import Any

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class CompatibleUnpickler(pickle.Unpickler):
    """兼容的pickle解包器，解决模块路径变更问题"""
    
    def find_class(self, module, name):
        """重写find_class方法来处理模块路径映射"""
        
        # 模块映射表
        module_mapping = {
            'fuel_prediction_models': 'src.fuel_prediction_models',
            'feature_engineering': 'src.feature_engineering', 
            'cp_clause_definitions': 'src.cp_clause_definitions',
            'data_analyzer': 'src.data_analyzer',
            'model_validation': 'src.model_validation'
        }
        
        # 如果模块在映射表中，使用新路径
        if module in module_mapping:
            module = module_mapping[module]
        
        try:
            return super().find_class(module, name)
        except (ImportError, AttributeError) as e:
            print(f"警告: 无法加载 {module}.{name}, 错误: {e}")
            # 返回一个占位符类或None
            return None

def load_model_safely(model_path: str) -> Any:
    """安全加载模型文件"""
    try:
        print(f"正在安全加载模型: {model_path}")
        
        with open(model_path, 'rb') as f:
            unpickler = CompatibleUnpickler(f)
            model_data = unpickler.load()
        
        print("✅ 模型加载成功")
        return model_data
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return None

def extract_model_info(model_data: Any) -> dict:
    """提取模型信息"""
    if model_data is None:
        return {}
    
    info = {}
    
    try:
        if isinstance(model_data, dict):
            # 检查船型预测器
            if 'ship_predictors' in model_data:
                ship_predictors = model_data['ship_predictors']
                if isinstance(ship_predictors, dict):
                    info['ship_types'] = list(ship_predictors.keys())
                    info['ship_count'] = len(ship_predictors)
            
            # 检查全局模型
            if 'global_model' in model_data:
                info['has_global_model'] = model_data['global_model'] is not None
            
            # 检查特征工程器
            if 'feature_engineer' in model_data:
                info['has_feature_engineer'] = model_data['feature_engineer'] is not None
        
    except Exception as e:
        print(f"提取模型信息时出错: {e}")
    
    return info

def create_simple_predictor_from_data(model_data: Any) -> dict:
    """从模型数据创建简化的预测器"""
    if model_data is None:
        return {}
    
    predictor_info = {}
    
    try:
        if isinstance(model_data, dict) and 'ship_predictors' in model_data:
            ship_predictors = model_data['ship_predictors']
            
            for ship_type, predictor_data in ship_predictors.items():
                if isinstance(predictor_data, dict):
                    # 提取性能指标
                    performance = predictor_data.get('performance_metrics', {})
                    feature_importance = predictor_data.get('feature_importance', {})
                    
                    predictor_info[ship_type] = {
                        'best_model_name': predictor_data.get('best_model_name', 'Unknown'),
                        'performance': performance,
                        'top_features': list(feature_importance.keys())[:5] if feature_importance else []
                    }
    
    except Exception as e:
        print(f"创建简化预测器时出错: {e}")
    
    return predictor_info

def main():
    """测试模型加载"""
    model_path = 'models/fuel_prediction_models.pkl'
    
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return
    
    # 加载模型
    model_data = load_model_safely(model_path)
    
    if model_data:
        # 提取模型信息
        info = extract_model_info(model_data)
        print(f"\n📊 模型信息:")
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # 创建简化预测器
        predictor_info = create_simple_predictor_from_data(model_data)
        if predictor_info:
            print(f"\n🚢 船型预测器信息:")
            for ship_type, data in predictor_info.items():
                print(f"   {ship_type}:")
                print(f"     最佳模型: {data['best_model_name']}")
                if data['top_features']:
                    print(f"     重要特征: {', '.join(data['top_features'])}")
    
    print(f"\n✅ 模型加载测试完成")

if __name__ == "__main__":
    main()
