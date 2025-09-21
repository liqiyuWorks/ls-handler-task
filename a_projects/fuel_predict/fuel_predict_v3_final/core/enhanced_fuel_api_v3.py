#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版船舶油耗预测API V3.0
Enhanced Ship Fuel Consumption Prediction API V3.0

支持更多输入条件的高精度预测API：
- 船舶类型 (ship_type) - 必需
- 航行速度 (speed) - 必需  
- 载重吨 (dwt) - 可选
- 船龄 (ship_age) - 可选，新增
- 载重状态 (load_condition) - 可选，新增
- 船舶尺寸 (draft, length) - 可选，新增
- 地理位置 (latitude, longitude) - 可选，新增
- 租约条款 (heavy_fuel_cp, light_fuel_cp, speed_cp) - 可选，新增

基于相关性分析优化的特征选择和模型训练

作者: 船舶油耗预测系统
日期: 2025-09-21
版本: 3.0
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
from enhanced_fuel_predictor_v3 import EnhancedFuelPredictorV3
import warnings
warnings.filterwarnings('ignore')

class EnhancedFuelAPIV3:
    """增强版船舶油耗预测API V3.0"""
    
    def __init__(self, model_path: str = None):
        """
        初始化API V3
        
        Args:
            model_path: 预训练模型路径 (可选)
        """
        self.predictor = EnhancedFuelPredictorV3()
        self.is_ready = False
        self.model_info = {}
        
        # 自动寻找最新的V3模型
        if model_path is None:
            model_path = self._find_latest_v3_model()
        
        if model_path and os.path.exists(model_path):
            self.is_ready = self.predictor.load_model(model_path)
            self.model_info = {
                'model_path': model_path,
                'loaded_at': datetime.now().isoformat(),
                'version': '3.0',
                'status': 'ready' if self.is_ready else 'failed'
            }
        
        if not self.is_ready:
            print("⚠️ 模型V3未加载成功，将使用增强规则预测")
    
    def _find_latest_v3_model(self) -> Optional[str]:
        """查找最新的V3模型文件"""
        possible_paths = [
            "models",
            "../models", 
            os.path.join(os.path.dirname(__file__), "..", "models")
        ]
        
        for model_dir in possible_paths:
            if os.path.exists(model_dir):
                model_files = [f for f in os.listdir(model_dir) 
                             if f.startswith('enhanced_fuel_model_v3_') and f.endswith('.pkl')]
                if model_files:
                    latest_model = sorted(model_files)[-1]
                    return os.path.join(model_dir, latest_model)
        
        return None
    
    def predict_enhanced(self, ship_type: str, speed: float, 
                        dwt: float = None, ship_age: float = None,
                        load_condition: str = 'Laden',
                        draft: float = None, length: float = None,
                        latitude: float = None, longitude: float = None,
                        heavy_fuel_cp: float = None, 
                        light_fuel_cp: float = None,
                        speed_cp: float = None,
                        **kwargs) -> Dict:
        """
        增强预测 - 支持更多输入条件
        
        Args:
            ship_type: 船舶类型 (必需)
                支持: 'Bulk Carrier', 'Container Ship', 'Crude Oil Tanker', 
                     'Chemical Tanker', 'General Cargo', 'Open Hatch Cargo'
            speed: 航行速度，单位：节 (必需)
            dwt: 载重吨，单位：吨 (可选)
            ship_age: 船龄，单位：年 (可选，新增)
            load_condition: 载重状态 (可选，新增)
                支持: 'Laden'(满载), 'Ballast'(压载)
            draft: 船舶吃水，单位：米 (可选，新增)
            length: 船舶总长度，单位：米 (可选，新增)
            latitude: 纬度 (可选，新增)
            longitude: 经度 (可选，新增)
            heavy_fuel_cp: 重油CP价格，单位：$/吨 (可选，新增)
            light_fuel_cp: 轻油CP价格，单位：$/吨 (可选，新增)
            speed_cp: 航速CP，单位：节 (可选，新增)
        
        Returns:
            预测结果字典
        """
        try:
            # 使用增强预测器
            result = self.predictor.predict_with_enhanced_features(
                ship_type=ship_type,
                speed=speed,
                dwt=dwt,
                ship_age=ship_age,
                load_condition=load_condition,
                draft=draft,
                length=length,
                latitude=latitude,
                longitude=longitude,
                heavy_fuel_cp=heavy_fuel_cp,
                light_fuel_cp=light_fuel_cp,
                speed_cp=speed_cp
            )
            
            # 增强结果信息
            result.update({
                'api_version': '3.0',
                'prediction_time': datetime.now().isoformat(),
                'data_source': 'NOON Reports with Enhanced Features',
                'model_status': 'v3_enhanced' if self.is_ready else 'enhanced_rules',
                'supported_features': [
                    'ship_type', 'speed', 'dwt', 'ship_age', 'load_condition',
                    'draft', 'length', 'coordinates', 'charter_party_terms'
                ]
            })
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'ship_type': ship_type,
                'speed': speed,
                'prediction_time': datetime.now().isoformat(),
                'status': 'failed',
                'api_version': '3.0'
            }
    
    def predict_with_ship_profile(self, ship_profile: Dict) -> Dict:
        """
        使用船舶档案进行预测
        
        Args:
            ship_profile: 船舶档案字典，包含所有船舶信息
        
        Returns:
            预测结果字典
        """
        # 从船舶档案提取参数
        return self.predict_enhanced(
            ship_type=ship_profile.get('ship_type'),
            speed=ship_profile.get('speed'),
            dwt=ship_profile.get('dwt'),
            ship_age=ship_profile.get('ship_age'),
            load_condition=ship_profile.get('load_condition', 'Laden'),
            draft=ship_profile.get('draft'),
            length=ship_profile.get('length'),
            latitude=ship_profile.get('latitude'),
            longitude=ship_profile.get('longitude'),
            heavy_fuel_cp=ship_profile.get('heavy_fuel_cp'),
            light_fuel_cp=ship_profile.get('light_fuel_cp'),
            speed_cp=ship_profile.get('speed_cp')
        )
    
    def analyze_feature_impact(self, base_case: Dict, variations: Dict) -> Dict:
        """
        分析不同特征对油耗的影响
        
        Args:
            base_case: 基准案例
            variations: 变化参数 {'feature_name': [value1, value2, ...]}
        
        Returns:
            特征影响分析结果
        """
        results = {
            'base_case': base_case.copy(),
            'base_prediction': None,
            'feature_impacts': {},
            'analysis_time': datetime.now().isoformat()
        }
        
        # 基准预测
        base_result = self.predict_enhanced(**base_case)
        if 'predicted_consumption' in base_result:
            results['base_prediction'] = base_result['predicted_consumption']
        else:
            return {'error': 'Base case prediction failed'}
        
        # 分析各特征影响
        for feature_name, values in variations.items():
            if feature_name not in base_case:
                continue
            
            feature_impacts = []
            for value in values:
                # 创建变化案例
                varied_case = base_case.copy()
                varied_case[feature_name] = value
                
                # 预测
                varied_result = self.predict_enhanced(**varied_case)
                if 'predicted_consumption' in varied_result:
                    impact = varied_result['predicted_consumption'] - results['base_prediction']
                    impact_pct = (impact / results['base_prediction']) * 100
                    
                    feature_impacts.append({
                        'value': value,
                        'predicted_consumption': varied_result['predicted_consumption'],
                        'impact_absolute': round(impact, 2),
                        'impact_percentage': round(impact_pct, 2)
                    })
            
            results['feature_impacts'][feature_name] = feature_impacts
        
        return results
    
    def optimize_for_target_consumption(self, target_consumption: float,
                                      ship_profile: Dict,
                                      optimize_parameter: str = 'speed',
                                      parameter_range: Tuple[float, float] = None) -> Dict:
        """
        为目标油耗优化参数
        
        Args:
            target_consumption: 目标油耗 (mt)
            ship_profile: 船舶档案
            optimize_parameter: 要优化的参数 ('speed', 'dwt', etc.)
            parameter_range: 参数范围 (min, max)
        
        Returns:
            优化结果
        """
        if optimize_parameter not in ship_profile:
            return {'error': f'Parameter {optimize_parameter} not found in ship profile'}
        
        # 设置默认范围
        if parameter_range is None:
            if optimize_parameter == 'speed':
                parameter_range = (8, 20)
            elif optimize_parameter == 'dwt':
                parameter_range = (20000, 200000)
            else:
                return {'error': f'Default range not defined for {optimize_parameter}'}
        
        min_val, max_val = parameter_range
        best_value = None
        best_prediction = None
        min_diff = float('inf')
        
        # 搜索最优值
        search_values = np.linspace(min_val, max_val, 50)
        optimization_results = []
        
        for value in search_values:
            test_profile = ship_profile.copy()
            test_profile[optimize_parameter] = value
            
            result = self.predict_with_ship_profile(test_profile)
            
            if 'predicted_consumption' in result:
                predicted = result['predicted_consumption']
                diff = abs(predicted - target_consumption)
                
                optimization_results.append({
                    'parameter_value': round(value, 2),
                    'predicted_consumption': predicted,
                    'difference': round(diff, 2)
                })
                
                if diff < min_diff:
                    min_diff = diff
                    best_value = value
                    best_prediction = predicted
        
        # 排序结果
        optimization_results.sort(key=lambda x: x['difference'])
        
        return {
            'target_consumption': target_consumption,
            'optimize_parameter': optimize_parameter,
            'parameter_range': parameter_range,
            'best_value': round(best_value, 2) if best_value else None,
            'best_prediction': round(best_prediction, 2) if best_prediction else None,
            'accuracy': f"±{min_diff:.2f}mt" if min_diff != float('inf') else None,
            'top_solutions': optimization_results[:5],
            'ship_profile': ship_profile
        }
    
    def compare_load_conditions(self, ship_profile: Dict) -> Dict:
        """
        比较不同载重状态下的油耗
        
        Args:
            ship_profile: 船舶档案
        
        Returns:
            载重状态对比结果
        """
        load_conditions = ['Laden', 'Ballast']
        comparison_results = []
        
        for condition in load_conditions:
            test_profile = ship_profile.copy()
            test_profile['load_condition'] = condition
            
            result = self.predict_with_ship_profile(test_profile)
            
            if 'predicted_consumption' in result:
                comparison_results.append({
                    'load_condition': condition,
                    'predicted_consumption': result['predicted_consumption'],
                    'confidence': result.get('confidence', 'Unknown')
                })
        
        # 计算差异
        if len(comparison_results) == 2:
            laden_consumption = comparison_results[0]['predicted_consumption']
            ballast_consumption = comparison_results[1]['predicted_consumption']
            difference = laden_consumption - ballast_consumption
            difference_pct = (difference / laden_consumption) * 100
            
            return {
                'ship_profile': ship_profile,
                'comparison_results': comparison_results,
                'consumption_difference': {
                    'absolute': round(difference, 2),
                    'percentage': round(difference_pct, 2)
                },
                'recommendation': f"压载状态可节约 {abs(difference):.2f}mt ({abs(difference_pct):.1f}%)" if difference > 0 else "满载状态更经济"
            }
        
        return {
            'ship_profile': ship_profile,
            'comparison_results': comparison_results,
            'error': 'Unable to compare load conditions'
        }
    
    def analyze_ship_age_impact(self, ship_profile: Dict,
                               age_range: Tuple[float, float] = (0, 25)) -> Dict:
        """
        分析船龄对油耗的影响
        
        Args:
            ship_profile: 船舶档案
            age_range: 船龄范围 (年)
        
        Returns:
            船龄影响分析结果
        """
        min_age, max_age = age_range
        ages = np.arange(min_age, max_age + 1, 2)  # 每2年一个点
        
        age_analysis = []
        
        for age in ages:
            test_profile = ship_profile.copy()
            test_profile['ship_age'] = age
            
            result = self.predict_with_ship_profile(test_profile)
            
            if 'predicted_consumption' in result:
                age_group = self._classify_age(age)
                age_analysis.append({
                    'ship_age': age,
                    'age_group': age_group,
                    'predicted_consumption': result['predicted_consumption']
                })
        
        if age_analysis:
            # 找出最经济船龄
            best_age = min(age_analysis, key=lambda x: x['predicted_consumption'])
            worst_age = max(age_analysis, key=lambda x: x['predicted_consumption'])
            
            efficiency_range = worst_age['predicted_consumption'] - best_age['predicted_consumption']
            
            return {
                'ship_profile': ship_profile,
                'age_range': age_range,
                'age_analysis': age_analysis,
                'most_efficient_age': best_age,
                'least_efficient_age': worst_age,
                'efficiency_range': round(efficiency_range, 2),
                'recommendation': f"最经济船龄: {best_age['ship_age']}年 ({best_age['age_group']})"
            }
        
        return {'error': 'Unable to analyze ship age impact'}
    
    def _classify_age(self, age: float) -> str:
        """分类船龄"""
        if age < 5:
            return '新船'
        elif age < 10:
            return '中等船龄'
        elif age < 20:
            return '老船'
        else:
            return '高龄船'
    
    def generate_comprehensive_report(self, ship_profile: Dict) -> Dict:
        """
        生成综合分析报告
        
        Args:
            ship_profile: 船舶档案
        
        Returns:
            综合分析报告
        """
        report = {
            'ship_profile': ship_profile,
            'analysis_time': datetime.now().isoformat(),
            'api_version': '3.0'
        }
        
        # 基础预测
        base_prediction = self.predict_with_ship_profile(ship_profile)
        report['base_prediction'] = base_prediction
        
        if 'predicted_consumption' not in base_prediction:
            report['error'] = 'Base prediction failed'
            return report
        
        # 载重状态对比
        if 'load_condition' in ship_profile:
            report['load_condition_analysis'] = self.compare_load_conditions(ship_profile)
        
        # 船龄影响分析
        if 'ship_age' in ship_profile:
            report['ship_age_analysis'] = self.analyze_ship_age_impact(ship_profile)
        
        # 速度优化
        speed_optimization = self.optimize_for_target_consumption(
            target_consumption=base_prediction['predicted_consumption'] * 0.9,  # 目标节约10%
            ship_profile=ship_profile,
            optimize_parameter='speed'
        )
        report['speed_optimization'] = speed_optimization
        
        # 特征影响分析
        if 'dwt' in ship_profile and 'ship_age' in ship_profile:
            variations = {
                'dwt': [ship_profile['dwt'] * 0.8, ship_profile['dwt'] * 1.2],
                'ship_age': [max(0, ship_profile['ship_age'] - 5), ship_profile['ship_age'] + 5]
            }
            report['feature_impact_analysis'] = self.analyze_feature_impact(ship_profile, variations)
        
        return report
    
    def get_api_status_v3(self) -> Dict:
        """获取API V3状态信息"""
        return {
            'api_version': '3.0',
            'model_loaded': self.is_ready,
            'model_info': self.model_info,
            'enhanced_features': {
                'required': ['ship_type', 'speed'],
                'optional': [
                    'dwt', 'ship_age', 'load_condition',
                    'draft', 'length', 'latitude', 'longitude',
                    'heavy_fuel_cp', 'light_fuel_cp', 'speed_cp'
                ]
            },
            'available_functions': [
                'predict_enhanced',
                'predict_with_ship_profile',
                'analyze_feature_impact',
                'optimize_for_target_consumption',
                'compare_load_conditions',
                'analyze_ship_age_impact',
                'generate_comprehensive_report'
            ],
            'supported_ship_types': [
                'Bulk Carrier',
                'Container Ship', 
                'Crude Oil Tanker',
                'Chemical Tanker',
                'General Cargo',
                'Open Hatch Cargo',
                'Other'
            ],
            'load_conditions': ['Laden', 'Ballast'],
            'optimization_parameters': ['speed', 'dwt'],
            'data_source': 'NOON Reports with Enhanced Feature Engineering',
            'last_updated': datetime.now().isoformat()
        }

def main():
    """演示API V3功能"""
    print("🚀 增强版船舶油耗预测API V3.0 演示")
    
    # 初始化API
    api = EnhancedFuelAPIV3()
    
    # 显示API状态
    status = api.get_api_status_v3()
    print(f"\n📊 API状态: {'✅ 就绪' if status['model_loaded'] else '⚠️ 增强规则模式'}")
    print(f"支持的增强特征: {len(status['enhanced_features']['optional'])}个")
    
    # 演示功能
    print("\n🧪 功能演示:")
    
    # 1. 基础增强预测
    print("\n1. 基础增强预测:")
    result = api.predict_enhanced(
        ship_type='Bulk Carrier',
        speed=12.0,
        dwt=75000,
        ship_age=8,
        load_condition='Laden',
        draft=12.5,
        length=225
    )
    print(f"   散货船(8年船龄,满载): {result.get('predicted_consumption', 'N/A')}mt")
    
    # 2. 船舶档案预测
    print("\n2. 船舶档案预测:")
    ship_profile = {
        'ship_type': 'Container Ship',
        'speed': 18.0,
        'dwt': 120000,
        'ship_age': 5,
        'load_condition': 'Laden',
        'latitude': 35.0,
        'longitude': 139.0,
        'heavy_fuel_cp': 650
    }
    
    profile_result = api.predict_with_ship_profile(ship_profile)
    print(f"   集装箱船档案预测: {profile_result.get('predicted_consumption', 'N/A')}mt")
    
    # 3. 载重状态对比
    print("\n3. 载重状态对比:")
    load_comparison = api.compare_load_conditions(ship_profile)
    if 'consumption_difference' in load_comparison:
        diff = load_comparison['consumption_difference']
        print(f"   满载vs压载差异: {diff['absolute']}mt ({diff['percentage']}%)")
    
    # 4. 船龄影响分析
    print("\n4. 船龄影响分析:")
    age_analysis = api.analyze_ship_age_impact(ship_profile)
    if 'most_efficient_age' in age_analysis:
        best_age = age_analysis['most_efficient_age']
        print(f"   最经济船龄: {best_age['ship_age']}年 ({best_age['predicted_consumption']}mt)")
    
    # 5. 速度优化
    print("\n5. 速度优化:")
    speed_opt = api.optimize_for_target_consumption(
        target_consumption=30.0,
        ship_profile=ship_profile,
        optimize_parameter='speed'
    )
    if 'best_value' in speed_opt:
        print(f"   目标30mt最佳速度: {speed_opt['best_value']}节")
    
    # 6. 特征影响分析
    print("\n6. 特征影响分析:")
    base_case = {'ship_type': 'Bulk Carrier', 'speed': 12.0, 'dwt': 75000, 'ship_age': 10}
    variations = {
        'ship_age': [5, 15, 20],
        'dwt': [50000, 100000, 150000]
    }
    
    impact_analysis = api.analyze_feature_impact(base_case, variations)
    if 'feature_impacts' in impact_analysis:
        for feature, impacts in impact_analysis['feature_impacts'].items():
            if impacts:
                max_impact = max(impacts, key=lambda x: abs(x['impact_percentage']))
                print(f"   {feature}最大影响: {max_impact['impact_percentage']}%")
    
    print("\n✅ API V3演示完成!")

if __name__ == "__main__":
    main()
