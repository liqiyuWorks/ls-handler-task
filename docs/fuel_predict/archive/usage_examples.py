#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统使用案例
包含完整的使用示例、API接口和实际应用场景

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_analyzer import ShipFuelDataAnalyzer
from src.cp_clause_definitions import CPClauseCalculator, ShipType, LoadCondition
from src.feature_engineering import ShipFuelFeatureEngineer
from src.fuel_prediction_models import MultiShipTypePredictor
from src.model_validation import ModelValidator

class FuelConsumptionPredictor:
    """船舶油耗预测API接口"""
    
    def __init__(self, model_path: str = None):
        """
        初始化预测器
        
        Args:
            model_path: 预训练模型路径
        """
        self.predictor_system = MultiShipTypePredictor()
        self.cp_calculator = CPClauseCalculator()
        self.is_trained = False
        
        if model_path:
            self.load_model(model_path)
    
    def train_from_data(self, data_path: str, target_col: str = '小时油耗(mt/h)'):
        """
        从数据文件训练模型
        
        Args:
            data_path: 训练数据路径
            target_col: 目标列名
        """
        print("开始从数据训练模型...")
        
        # 加载数据
        df = pd.read_csv(data_path)
        print(f"加载数据: {len(df)} 条记录")
        
        # 准备数据
        X, y = self.predictor_system.prepare_data(df, target_col=target_col)
        
        # 分割训练测试集
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 训练模型
        ship_performance = self.predictor_system.train_ship_type_models(X_train, y_train)
        global_performance = self.predictor_system.train_global_model(X_train, y_train)
        
        # 模型验证
        validator = ModelValidator(self.predictor_system)
        validation_results = validator.comprehensive_validation(X_test, y_test, X_train, y_train)
        
        self.is_trained = True
        
        print("模型训练完成！")
        return {
            'ship_performance': ship_performance,
            'global_performance': global_performance,
            'validation_results': validation_results
        }
    
    def predict_single_voyage(self, voyage_data: Dict) -> Dict:
        """
        预测单次航行的油耗
        
        Args:
            voyage_data: 航行数据字典
            
        Returns:
            预测结果字典
        """
        if not self.is_trained:
            raise ValueError("模型尚未训练，请先调用train_from_data()或load_model()")
        
        # 转换为DataFrame
        df = pd.DataFrame([voyage_data])
        
        # 添加必要的时间列（使用当前时间戳）
        import time
        if '报告时间' not in df.columns:
            df['报告时间'] = int(time.time() * 1000)  # 毫秒时间戳
        
        # 计算小时油耗（如果没有的话）
        if '小时油耗(mt/h)' not in df.columns:
            df['总油耗(mt)'] = df.get('重油IFO(mt)', 0) + df.get('轻油MDO/MGO(mt)', 0)
            df['小时油耗(mt/h)'] = np.where(
                df.get('航行时间(hrs)', 0) > 0,
                df['总油耗(mt)'] / df['航行时间(hrs)'],
                0
            )
        
        # 特征工程
        df_engineered = self.predictor_system.feature_engineer.engineer_features(df, fit=False)
        
        # 准备预测特征
        feature_cols = [col for col in df_engineered.columns if 
                       col not in ['报告时间', 'MMSI', 'IMO', '航次ID'] and
                       df_engineered[col].dtype in ['int64', 'float64']]
        
        X_pred = df_engineered[feature_cols + ['船舶类型']].fillna(0)
        
        # 预测
        prediction = self.predictor_system.predict(X_pred)[0]
        
        # CP条款分析
        cp_analysis = self._analyze_cp_performance(voyage_data, prediction)
        
        # 行业对比
        industry_comparison = self._compare_with_industry_standards(voyage_data, prediction)
        
        return {
            'predicted_fuel_consumption': prediction,
            'unit': 'mt/h',
            'cp_clause_analysis': cp_analysis,
            'industry_comparison': industry_comparison,
            'confidence_level': self._calculate_confidence(voyage_data),
            'recommendations': self._generate_recommendations(voyage_data, prediction)
        }
    
    def predict_voyage_plan(self, voyage_plan: List[Dict]) -> Dict:
        """
        预测航行计划的总油耗
        
        Args:
            voyage_plan: 航行计划列表，每个元素包含航段信息
            
        Returns:
            总体预测结果
        """
        segment_predictions = []
        total_fuel = 0
        total_distance = 0
        total_time = 0
        
        for i, segment in enumerate(voyage_plan):
            try:
                prediction = self.predict_single_voyage(segment)
                
                # 计算该航段的总油耗
                segment_time = segment.get('航行时间(hrs)', 24)  # 默认24小时
                segment_fuel = prediction['predicted_fuel_consumption'] * segment_time
                
                segment_result = {
                    'segment_id': i + 1,
                    'hourly_consumption': prediction['predicted_fuel_consumption'],
                    'segment_time': segment_time,
                    'segment_fuel': segment_fuel,
                    'distance': segment.get('航行距离(nm)', 0),
                    'speed': segment.get('平均速度(kts)', 0)
                }
                
                segment_predictions.append(segment_result)
                total_fuel += segment_fuel
                total_distance += segment.get('航行距离(nm)', 0)
                total_time += segment_time
                
            except Exception as e:
                print(f"航段 {i+1} 预测失败: {e}")
                continue
        
        # 计算总体指标
        avg_speed = total_distance / total_time if total_time > 0 else 0
        fuel_efficiency = total_distance / total_fuel if total_fuel > 0 else 0
        
        return {
            'total_fuel_consumption': total_fuel,
            'total_distance': total_distance,
            'total_time': total_time,
            'average_speed': avg_speed,
            'fuel_efficiency': fuel_efficiency,
            'segment_details': segment_predictions,
            'voyage_summary': {
                'segments_count': len(segment_predictions),
                'successful_predictions': len(segment_predictions),
                'unit_consumption_per_nm': total_fuel / total_distance if total_distance > 0 else 0
            }
        }
    
    def optimize_speed_for_fuel(self, voyage_data: Dict, speed_range: Tuple[float, float] = (8, 18),
                               step: float = 0.5) -> Dict:
        """
        优化航行速度以降低油耗
        
        Args:
            voyage_data: 基础航行数据
            speed_range: 速度范围 (最小, 最大)
            step: 速度步长
            
        Returns:
            优化结果
        """
        speeds = np.arange(speed_range[0], speed_range[1] + step, step)
        optimization_results = []
        
        base_data = voyage_data.copy()
        
        for speed in speeds:
            try:
                # 更新速度
                test_data = base_data.copy()
                test_data['平均速度(kts)'] = speed
                
                # 预测油耗
                prediction = self.predict_single_voyage(test_data)
                hourly_consumption = prediction['predicted_fuel_consumption']
                
                # 计算航行时间（假设距离固定）
                distance = test_data.get('航行距离(nm)', 240)  # 默认240海里
                time_hours = distance / speed if speed > 0 else 0
                total_fuel = hourly_consumption * time_hours
                
                optimization_results.append({
                    'speed': speed,
                    'hourly_consumption': hourly_consumption,
                    'voyage_time': time_hours,
                    'total_fuel': total_fuel,
                    'fuel_per_nm': total_fuel / distance if distance > 0 else 0
                })
                
            except Exception as e:
                print(f"速度 {speed} 优化失败: {e}")
                continue
        
        if not optimization_results:
            return {'error': '优化失败'}
        
        # 找到最优速度
        optimal_result = min(optimization_results, key=lambda x: x['total_fuel'])
        
        return {
            'optimal_speed': optimal_result['speed'],
            'optimal_consumption': optimal_result['total_fuel'],
            'time_savings': base_data.get('航行时间(hrs)', 24) - optimal_result['voyage_time'],
            'fuel_savings': self.predict_single_voyage(base_data)['predicted_fuel_consumption'] * 
                          base_data.get('航行时间(hrs)', 24) - optimal_result['total_fuel'],
            'optimization_curve': optimization_results,
            'recommendations': self._generate_speed_recommendations(optimal_result)
        }
    
    def _analyze_cp_performance(self, voyage_data: Dict, predicted_consumption: float) -> Dict:
        """分析CP条款性能"""
        ship_type_str = voyage_data.get('船舶类型', 'BULK CARRIER')
        load_condition_str = voyage_data.get('载重状态', 'Laden')
        dwt = voyage_data.get('船舶载重(t)', 75000)
        speed = voyage_data.get('平均速度(kts)', 12)
        
        try:
            # 转换为枚举类型
            ship_type = ShipType(ship_type_str)
            load_condition = LoadCondition(load_condition_str)
        except ValueError:
            # 使用默认值
            ship_type = ShipType.BULK_CARRIER
            load_condition = LoadCondition.LADEN
        
        # 计算CP条款标准
        warranted_speed = self.cp_calculator.calculate_warranted_speed(
            ship_type, load_condition, dwt
        )
        warranted_consumption = self.cp_calculator.calculate_warranted_consumption(
            ship_type, load_condition, dwt, speed
        )
        
        # 计算偏差
        deviation = self.cp_calculator.calculate_performance_deviation(
            speed, predicted_consumption, warranted_speed, warranted_consumption['total']
        )
        
        return {
            'warranted_speed': warranted_speed,
            'warranted_consumption': warranted_consumption,
            'performance_deviation': deviation,
            'cp_compliance': deviation['performance_index'] > 80
        }
    
    def _compare_with_industry_standards(self, voyage_data: Dict, predicted_consumption: float) -> Dict:
        """与行业标准对比"""
        ship_type = voyage_data.get('船舶类型', 'BULK CARRIER')
        
        # 行业平均油耗标准 (mt/day)
        industry_standards = {
            'BULK CARRIER': 25.0,
            'CONTAINER SHIP': 180.0,
            'TANKER': 35.0,
            'General Cargo Ship': 15.0,
            'OPEN HATCH CARGO SHIP': 28.0
        }
        
        daily_consumption = predicted_consumption * 24  # 转换为日油耗
        standard = industry_standards.get(ship_type, 25.0)
        
        deviation = (daily_consumption - standard) / standard * 100
        
        return {
            'predicted_daily_consumption': daily_consumption,
            'industry_standard': standard,
            'deviation_percent': deviation,
            'performance_rating': self._get_performance_rating(deviation)
        }
    
    def _get_performance_rating(self, deviation: float) -> str:
        """获取性能评级"""
        if deviation < -15:
            return 'Excellent'
        elif deviation < -5:
            return 'Good'
        elif deviation < 5:
            return 'Average'
        elif deviation < 15:
            return 'Below Average'
        else:
            return 'Poor'
    
    def _calculate_confidence(self, voyage_data: Dict) -> str:
        """计算预测置信度"""
        # 基于数据完整性和船型支持情况计算置信度
        confidence_score = 100
        
        # 检查关键字段
        required_fields = ['船舶类型', '平均速度(kts)', '船舶载重(t)', '载重状态']
        missing_fields = [field for field in required_fields if field not in voyage_data or voyage_data[field] is None]
        
        confidence_score -= len(missing_fields) * 15
        
        # 检查船型支持
        ship_type = voyage_data.get('船舶类型', '')
        if ship_type not in self.predictor_system.ship_predictors:
            confidence_score -= 20
        
        # 检查数值合理性
        speed = voyage_data.get('平均速度(kts)', 0)
        if speed < 5 or speed > 25:
            confidence_score -= 10
        
        if confidence_score >= 90:
            return 'High'
        elif confidence_score >= 70:
            return 'Medium'
        else:
            return 'Low'
    
    def _generate_recommendations(self, voyage_data: Dict, predicted_consumption: float) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        speed = voyage_data.get('平均速度(kts)', 12)
        ship_type = voyage_data.get('船舶类型', 'BULK CARRIER')
        
        # 速度优化建议
        if speed > 15:
            recommendations.append("考虑适当降低航行速度以节省燃料，通常速度降低10%可节省约25%的燃料")
        
        if speed < 8:
            recommendations.append("当前速度较低，可能影响航行效率，建议评估时间成本")
        
        # 载重状态建议
        load_condition = voyage_data.get('载重状态', 'Laden')
        if load_condition == 'Ballast':
            recommendations.append("压载状态下建议优化航线以减少空载距离")
        
        # 天气因素建议
        if predicted_consumption > 30:  # 高油耗
            recommendations.append("预测油耗较高，建议关注天气海况，必要时调整航线或时间")
        
        # 船舶维护建议
        recommendations.append("定期进行船体清洁和主机保养以维持最佳燃油效率")
        
        return recommendations
    
    def _generate_speed_recommendations(self, optimal_result: Dict) -> List[str]:
        """生成速度优化建议"""
        recommendations = []
        
        optimal_speed = optimal_result['speed']
        
        recommendations.append(f"建议航行速度: {optimal_speed:.1f} knots")
        recommendations.append(f"预计航行时间: {optimal_result['voyage_time']:.1f} 小时")
        recommendations.append(f"预计总油耗: {optimal_result['total_fuel']:.1f} mt")
        
        if optimal_speed < 10:
            recommendations.append("最优速度较低，适合成本优先的航行计划")
        elif optimal_speed > 16:
            recommendations.append("最优速度较高，适合时间敏感的航行计划")
        else:
            recommendations.append("最优速度适中，平衡了时间和成本效益")
        
        return recommendations
    
    def save_model(self, save_path: str):
        """保存模型"""
        self.predictor_system.save_models(save_path)
    
    def load_model(self, load_path: str):
        """加载模型"""
        self.predictor_system.load_models(load_path)
        self.is_trained = True

def demo_basic_usage():
    """基础使用演示"""
    print("="*60)
    print("船舶油耗预测系统 - 基础使用演示")
    print("="*60)
    
    # 创建预测器
    predictor = FuelConsumptionPredictor()
    
    # 从数据训练模型
    data_path = '../data/油耗数据ALL（0804）.csv'
    training_results = predictor.train_from_data(data_path)
    
    print(f"\n训练完成！训练了 {len(training_results['ship_performance'])} 个船型模型")
    
    # 单次航行预测示例
    print("\n" + "="*40)
    print("单次航行预测示例")
    print("="*40)
    
    voyage_data = {
        '船舶类型': 'BULK CARRIER',
        '平均速度(kts)': 12.5,
        '船舶载重(t)': 75000,
        '船舶吃水(m)': 14.2,
        '船舶总长度(m)': 225,
        '载重状态': 'Laden',
        '航行距离(nm)': 240,
        '航行时间(hrs)': 20,
        '重油cp': 24.0,
        '轻油cp': 0.0,
        '航速cp': 12.0,
        '船龄': 15
    }
    
    prediction_result = predictor.predict_single_voyage(voyage_data)
    
    print(f"预测结果:")
    print(f"  小时油耗: {prediction_result['predicted_fuel_consumption']:.2f} mt/h")
    print(f"  置信度: {prediction_result['confidence_level']}")
    print(f"  CP条款合规: {prediction_result['cp_clause_analysis']['cp_compliance']}")
    print(f"  行业对比评级: {prediction_result['industry_comparison']['performance_rating']}")
    
    print(f"\n优化建议:")
    for i, rec in enumerate(prediction_result['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    return predictor

def demo_voyage_planning():
    """航行计划演示"""
    print("\n" + "="*40)
    print("航行计划预测演示")
    print("="*40)
    
    # 使用已训练的预测器
    predictor = FuelConsumptionPredictor()
    
    # 模拟加载已训练模型
    try:
        model_path = '/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/fuel_prediction_models.pkl'
        predictor.load_model(model_path)
        print("已加载预训练模型")
    except:
        print("预训练模型不存在，需要先运行基础演示")
        return
    
    # 定义航行计划
    voyage_plan = [
        {  # 第一航段：出港
            '船舶类型': 'BULK CARRIER',
            '平均速度(kts)': 8.0,
            '船舶载重(t)': 75000,
            '船舶吃水(m)': 14.2,
            '船舶总长度(m)': 225,
            '载重状态': 'Laden',
            '航行距离(nm)': 50,
            '航行时间(hrs)': 6,
            '重油cp': 24.0,
            '航速cp': 12.0,
            '船龄': 15
        },
        {  # 第二航段：海上航行
            '船舶类型': 'BULK CARRIER',
            '平均速度(kts)': 13.0,
            '船舶载重(t)': 75000,
            '船舶吃水(m)': 14.2,
            '船舶总长度(m)': 225,
            '载重状态': 'Laden',
            '航行距离(nm)': 1200,
            '航行时间(hrs)': 92,
            '重油cp': 24.0,
            '航速cp': 12.0,
            '船龄': 15
        },
        {  # 第三航段：进港
            '船舶类型': 'BULK CARRIER',
            '平均速度(kts)': 6.0,
            '船舶载重(t)': 75000,
            '船舶吃水(m)': 14.2,
            '船舶总长度(m)': 225,
            '载重状态': 'Laden',
            '航行距离(nm)': 30,
            '航行时间(hrs)': 5,
            '重油cp': 24.0,
            '航速cp': 12.0,
            '船龄': 15
        }
    ]
    
    # 预测航行计划
    plan_result = predictor.predict_voyage_plan(voyage_plan)
    
    print(f"航行计划预测结果:")
    print(f"  总油耗: {plan_result['total_fuel_consumption']:.1f} mt")
    print(f"  总距离: {plan_result['total_distance']:.0f} nm")
    print(f"  总时间: {plan_result['total_time']:.0f} 小时")
    print(f"  平均速度: {plan_result['average_speed']:.1f} kts")
    print(f"  燃油效率: {plan_result['fuel_efficiency']:.2f} nm/mt")
    
    print(f"\n各航段详情:")
    for segment in plan_result['segment_details']:
        print(f"  航段 {segment['segment_id']}:")
        print(f"    小时油耗: {segment['hourly_consumption']:.2f} mt/h")
        print(f"    航段油耗: {segment['segment_fuel']:.1f} mt")
        print(f"    距离: {segment['distance']:.0f} nm")
        print(f"    速度: {segment['speed']:.1f} kts")

def demo_speed_optimization():
    """速度优化演示"""
    print("\n" + "="*40)
    print("速度优化演示")
    print("="*40)
    
    # 使用已训练的预测器
    predictor = FuelConsumptionPredictor()
    
    try:
        model_path = '/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/fuel_prediction_models.pkl'
        predictor.load_model(model_path)
    except:
        print("预训练模型不存在，需要先运行基础演示")
        return
    
    # 基础航行数据
    voyage_data = {
        '船舶类型': 'BULK CARRIER',
        '船舶载重(t)': 75000,
        '船舶吃水(m)': 14.2,
        '船舶总长度(m)': 225,
        '载重状态': 'Laden',
        '航行距离(nm)': 1000,
        '重油cp': 24.0,
        '航速cp': 12.0,
        '船龄': 15
    }
    
    # 速度优化
    optimization_result = predictor.optimize_speed_for_fuel(
        voyage_data, 
        speed_range=(8, 16), 
        step=0.5
    )
    
    print(f"速度优化结果:")
    print(f"  最优速度: {optimization_result['optimal_speed']:.1f} kts")
    print(f"  最优总油耗: {optimization_result['optimal_consumption']:.1f} mt")
    print(f"  节省燃料: {optimization_result['fuel_savings']:.1f} mt")
    
    print(f"\n优化建议:")
    for rec in optimization_result['recommendations']:
        print(f"  - {rec}")
    
    # 显示优化曲线的关键点
    curve = optimization_result['optimization_curve']
    print(f"\n速度-油耗关系 (前5个点):")
    for point in curve[:5]:
        print(f"  {point['speed']:.1f} kts -> {point['total_fuel']:.1f} mt (航行时间: {point['voyage_time']:.1f}h)")

def demo_comprehensive_analysis():
    """综合分析演示"""
    print("\n" + "="*60)
    print("综合分析演示")
    print("="*60)
    
    # 数据分析
    print("1. 数据分析")
    analyzer = ShipFuelDataAnalyzer('/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/油耗数据ALL（0804）.csv')
    
    # 基础统计
    stats = analyzer.get_basic_statistics()
    print(f"   数据总量: {stats['数据总量']:,} 条")
    print(f"   船舶数量: {stats['船舶数量']} 艘")
    
    # 船型分析
    ship_analysis = analyzer.analyze_ship_types()
    print(f"   分析了 {len(ship_analysis)} 种船型")
    
    print("\n2. CP条款计算")
    cp_calculator = CPClauseCalculator()
    
    # 示例计算
    warranted_speed = cp_calculator.calculate_warranted_speed(
        ShipType.BULK_CARRIER, LoadCondition.LADEN, 75000
    )
    print(f"   散货船保证航速: {warranted_speed} kts")
    
    print("\n3. 模型预测")
    # 这里可以展示模型预测的关键指标
    print("   已完成多船型预测模型训练")
    print("   支持实时预测和批量处理")
    print("   提供CP条款合规性分析")
    
    print("\n4. 业务应用")
    print("   - 航行计划优化")
    print("   - 燃料成本控制")
    print("   - CP条款性能评估")
    print("   - 船队管理决策支持")

def main():
    """主演示函数"""
    print("船舶油耗预测系统 - 完整使用案例演示")
    print("="*80)
    
    try:
        # 1. 基础使用演示
        predictor = demo_basic_usage()
        
        # 2. 航行计划演示
        demo_voyage_planning()
        
        # 3. 速度优化演示
        demo_speed_optimization()
        
        # 4. 综合分析演示
        demo_comprehensive_analysis()
        
        print("\n" + "="*80)
        print("所有演示完成！")
        print("系统已准备好用于实际业务场景")
        print("="*80)
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        print("请检查数据文件是否存在，以及依赖包是否安装完整")

if __name__ == "__main__":
    main()
