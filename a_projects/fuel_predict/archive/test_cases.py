#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统测试用例
Comprehensive Test Cases for Ship Fuel Consumption Prediction

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pandas as pd
import numpy as np
import json
import time
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction_api import FuelPredictionAPI
from src.data_analyzer import ShipFuelDataAnalyzer
from src.cp_clause_definitions import CPClauseCalculator, ShipType, LoadCondition

class TestCaseRunner:
    """测试用例运行器"""
    
    def __init__(self):
        self.api = FuelPredictionAPI('models/fuel_prediction_models.pkl')
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def create_test_voyages(self) -> List[Dict]:
        """创建测试航行数据"""
        test_voyages = [
            # 测试用例1: 标准散货船满载
            {
                'case_id': 'TC001',
                'description': '标准散货船满载航行',
                'ship_data': {
                    '船舶类型': 'BULK CARRIER',
                    '平均速度(kts)': 12.5,
                    '船舶载重(t)': 75000,
                    '船舶吃水(m)': 14.2,
                    '船舶总长度(m)': 225,
                    '载重状态': 'Laden',
                    '航行距离(nm)': 240,
                    '航行时间(hrs)': 20,
                    '重油IFO(mt)': 20.5,
                    '轻油MDO/MGO(mt)': 1.5,
                    '重油cp': 24.0,
                    '轻油cp': 0.0,
                    '航速cp': 12.0,
                    '船龄': 15
                },
                'expected_range': (18, 28),
                'expected_confidence': 'High'
            },
            
            # 测试用例2: 散货船压载
            {
                'case_id': 'TC002',
                'description': '散货船压载航行',
                'ship_data': {
                    '船舶类型': 'BULK CARRIER',
                    '平均速度(kts)': 14.0,
                    '船舶载重(t)': 75000,
                    '船舶吃水(m)': 8.5,
                    '船舶总长度(m)': 225,
                    '载重状态': 'Ballast',
                    '航行距离(nm)': 300,
                    '航行时间(hrs)': 22,
                    '重油IFO(mt)': 18.0,
                    '轻油MDO/MGO(mt)': 1.0,
                    '重油cp': 22.0,
                    '轻油cp': 0.0,
                    '航速cp': 13.0,
                    '船龄': 12
                },
                'expected_range': (15, 25),
                'expected_confidence': 'High'
            },
            
            # 测试用例3: 开舱口货船
            {
                'case_id': 'TC003',
                'description': '开舱口货船满载',
                'ship_data': {
                    '船舶类型': 'OPEN HATCH CARGO SHIP',
                    '平均速度(kts)': 13.0,
                    '船舶载重(t)': 62000,
                    '船舶吃水(m)': 13.3,
                    '船舶总长度(m)': 202,
                    '载重状态': 'Laden',
                    '航行距离(nm)': 280,
                    '航行时间(hrs)': 22,
                    '重油IFO(mt)': 25.0,
                    '轻油MDO/MGO(mt)': 1.2,
                    '重油cp': 27.0,
                    '轻油cp': 0.0,
                    '航速cp': 13.4,
                    '船龄': 8
                },
                'expected_range': (22, 35),
                'expected_confidence': 'High'
            },
            
            # 测试用例4: 化学品油轮
            {
                'case_id': 'TC004',
                'description': '化学品油轮压载',
                'ship_data': {
                    '船舶类型': 'CHEMICAL/PRODUCTS TANKER',
                    '平均速度(kts)': 11.8,
                    '船舶载重(t)': 45000,
                    '船舶吃水(m)': 9.2,
                    '船舶总长度(m)': 183,
                    '载重状态': 'Ballast',
                    '航行距离(nm)': 180,
                    '航行时间(hrs)': 15,
                    '重油IFO(mt)': 15.5,
                    '轻油MDO/MGO(mt)': 0.8,
                    '重油cp': 18.0,
                    '轻油cp': 1.0,
                    '航速cp': 12.5,
                    '船龄': 10
                },
                'expected_range': (14, 22),
                'expected_confidence': 'Medium'
            },
            
            # 测试用例5: 杂货船
            {
                'case_id': 'TC005',
                'description': '杂货船满载',
                'ship_data': {
                    '船舶类型': 'GENERAL CARGO SHIP',
                    '平均速度(kts)': 11.5,
                    '船舶载重(t)': 25000,
                    '船舶吃水(m)': 8.8,
                    '船舶总长度(m)': 150,
                    '载重状态': 'Laden',
                    '航行距离(nm)': 200,
                    '航行时间(hrs)': 18,
                    '重油IFO(mt)': 12.0,
                    '轻油MDO/MGO(mt)': 0.8,
                    '重油cp': 14.0,
                    '轻油cp': 1.2,
                    '航速cp': 11.5,
                    '船龄': 18
                },
                'expected_range': (10, 18),
                'expected_confidence': 'Medium'
            },
            
            # 测试用例6: 高速航行测试
            {
                'case_id': 'TC006',
                'description': '高速航行测试',
                'ship_data': {
                    '船舶类型': 'BULK CARRIER',
                    '平均速度(kts)': 16.5,
                    '船舶载重(t)': 80000,
                    '船舶吃水(m)': 14.8,
                    '船舶总长度(m)': 230,
                    '载重状态': 'Laden',
                    '航行距离(nm)': 320,
                    '航行时间(hrs)': 20,
                    '重油IFO(mt)': 35.0,
                    '轻油MDO/MGO(mt)': 2.0,
                    '重油cp': 28.0,
                    '轻油cp': 0.0,
                    '航速cp': 14.0,
                    '船龄': 8
                },
                'expected_range': (30, 45),
                'expected_confidence': 'High'
            },
            
            # 测试用例7: 低速航行测试
            {
                'case_id': 'TC007',
                'description': '低速航行测试',
                'ship_data': {
                    '船舶类型': 'BULK CARRIER',
                    '平均速度(kts)': 9.0,
                    '船舶载重(t)': 70000,
                    '船舶吃水(m)': 13.8,
                    '船舶总长度(m)': 220,
                    '载重状态': 'Laden',
                    '航行距离(nm)': 180,
                    '航行时间(hrs)': 20,
                    '重油IFO(mt)': 15.0,
                    '轻油MDO/MGO(mt)': 1.0,
                    '重油cp': 20.0,
                    '轻油cp': 0.0,
                    '航速cp': 12.0,
                    '船龄': 20
                },
                'expected_range': (12, 20),
                'expected_confidence': 'High'
            }
        ]
        
        return test_voyages
    
    def run_single_test(self, test_case: Dict) -> Dict:
        """运行单个测试用例"""
        case_id = test_case['case_id']
        description = test_case['description']
        ship_data = test_case['ship_data']
        expected_range = test_case['expected_range']
        expected_confidence = test_case['expected_confidence']
        
        print(f"\n🧪 运行测试 {case_id}: {description}")
        
        try:
            # 执行预测
            start_time = time.time()
            result = self.api.predict_single_voyage(ship_data)
            execution_time = time.time() - start_time
            
            predicted_consumption = result['predicted_fuel_consumption']
            confidence = result['confidence']
            
            # 验证结果
            in_range = expected_range[0] <= predicted_consumption <= expected_range[1]
            confidence_match = confidence == expected_confidence or confidence in ['High', 'Medium', 'Low']
            
            status = 'PASS' if in_range and confidence_match else 'FAIL'
            
            if status == 'PASS':
                self.passed += 1
                print(f"✅ {status}: {predicted_consumption:.2f} mt/h (预期: {expected_range[0]}-{expected_range[1]})")
            else:
                self.failed += 1
                print(f"❌ {status}: {predicted_consumption:.2f} mt/h (预期: {expected_range[0]}-{expected_range[1]})")
            
            print(f"   置信度: {confidence} (预期: {expected_confidence})")
            print(f"   执行时间: {execution_time:.3f}秒")
            
            # 记录测试结果
            test_result = {
                'case_id': case_id,
                'description': description,
                'ship_type': ship_data['船舶类型'],
                'speed': ship_data['平均速度(kts)'],
                'dwt': ship_data['船舶载重(t)'],
                'load_condition': ship_data['载重状态'],
                'predicted_consumption': predicted_consumption,
                'expected_range': expected_range,
                'confidence': confidence,
                'expected_confidence': expected_confidence,
                'execution_time': execution_time,
                'status': status,
                'in_range': in_range,
                'confidence_match': confidence_match,
                'recommendations': result.get('recommendations', []),
                'method': result.get('method', 'unknown')
            }
            
            return test_result
            
        except Exception as e:
            self.failed += 1
            print(f"❌ ERROR: {e}")
            
            return {
                'case_id': case_id,
                'description': description,
                'status': 'ERROR',
                'error': str(e),
                'execution_time': 0
            }
    
    def run_performance_tests(self) -> Dict:
        """运行性能测试"""
        print(f"\n⚡ 性能测试")
        print("-" * 40)
        
        # 创建大批量测试数据
        test_voyage = {
            '船舶类型': 'BULK CARRIER',
            '平均速度(kts)': 12.5,
            '船舶载重(t)': 75000,
            '载重状态': 'Laden',
            '航行距离(nm)': 240,
            '航行时间(hrs)': 20
        }
        
        batch_sizes = [1, 10, 50, 100]
        performance_results = {}
        
        for batch_size in batch_sizes:
            print(f"测试批量大小: {batch_size}")
            
            # 创建批量数据
            batch_data = [test_voyage.copy() for _ in range(batch_size)]
            
            # 测试批量预测性能
            start_time = time.time()
            batch_results = self.api.batch_predict(batch_data)
            execution_time = time.time() - start_time
            
            avg_time_per_prediction = execution_time / batch_size if batch_size > 0 else 0
            
            performance_results[f'batch_{batch_size}'] = {
                'batch_size': batch_size,
                'total_time': execution_time,
                'avg_time_per_prediction': avg_time_per_prediction,
                'throughput': batch_size / execution_time if execution_time > 0 else 0
            }
            
            print(f"   总时间: {execution_time:.3f}秒")
            print(f"   平均每次预测: {avg_time_per_prediction:.3f}秒")
            print(f"   吞吐量: {batch_size / execution_time:.1f} 预测/秒")
        
        return performance_results
    
    def run_stress_tests(self) -> Dict:
        """运行压力测试"""
        print(f"\n🔥 压力测试")
        print("-" * 40)
        
        stress_results = {}
        
        # 测试极端值处理
        extreme_cases = [
            {'description': '极小船舶', '船舶载重(t)': 1000, '平均速度(kts)': 8.0},
            {'description': '极大船舶', '船舶载重(t)': 400000, '平均速度(kts)': 15.0},
            {'description': '极低速度', '船舶载重(t)': 75000, '平均速度(kts)': 3.0},
            {'description': '极高速度', '船舶载重(t)': 75000, '平均速度(kts)': 25.0},
            {'description': '缺失数据', '船舶载重(t)': None, '平均速度(kts)': None}
        ]
        
        base_data = {
            '船舶类型': 'BULK CARRIER',
            '载重状态': 'Laden',
            '航行距离(nm)': 240,
            '航行时间(hrs)': 20
        }
        
        for case in extreme_cases:
            test_data = base_data.copy()
            test_data.update({k: v for k, v in case.items() if k != 'description'})
            
            try:
                result = self.api.predict_single_voyage(test_data)
                status = 'PASS' if result['predicted_fuel_consumption'] > 0 else 'FAIL'
                stress_results[case['description']] = {
                    'status': status,
                    'prediction': result['predicted_fuel_consumption'],
                    'confidence': result['confidence']
                }
                print(f"   {case['description']}: {status} ({result['predicted_fuel_consumption']:.2f} mt/h)")
            except Exception as e:
                stress_results[case['description']] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
                print(f"   {case['description']}: ERROR - {e}")
        
        return stress_results
    
    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("🚢 船舶油耗预测系统 - 完整测试套件")
        print("=" * 60)
        
        start_time = time.time()
        
        # 1. 功能测试
        print("\n📋 功能测试")
        print("=" * 40)
        
        test_voyages = self.create_test_voyages()
        
        for test_case in test_voyages:
            result = self.run_single_test(test_case)
            self.test_results.append(result)
        
        # 2. 性能测试
        performance_results = self.run_performance_tests()
        
        # 3. 压力测试
        stress_results = self.run_stress_tests()
        
        total_time = time.time() - start_time
        
        # 生成测试报告
        test_report = {
            'summary': {
                'total_tests': len(self.test_results),
                'passed': self.passed,
                'failed': self.failed,
                'pass_rate': (self.passed / len(self.test_results) * 100) if self.test_results else 0,
                'total_execution_time': total_time
            },
            'functional_tests': self.test_results,
            'performance_tests': performance_results,
            'stress_tests': stress_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 打印测试总结
        print(f"\n{'=' * 60}")
        print("🎯 测试总结")
        print(f"{'=' * 60}")
        print(f"总测试数: {len(self.test_results)}")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"通过率: {self.passed / len(self.test_results) * 100:.1f}%")
        print(f"总执行时间: {total_time:.2f}秒")
        
        # 保存测试报告
        report_path = 'outputs/test_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 测试报告已保存: {report_path}")
        
        return test_report
    
    def generate_prediction_results_file(self):
        """生成预测结果文件"""
        print(f"\n📄 生成预测结果文件")
        print("-" * 40)
        
        # 创建详细的预测结果
        prediction_results = []
        
        # 使用测试用例生成预测结果
        test_voyages = self.create_test_voyages()
        
        for test_case in test_voyages:
            ship_data = test_case['ship_data']
            
            # 执行预测
            result = self.api.predict_single_voyage(ship_data)
            
            # CP条款分析
            cp_analysis = result.get('cp_clause_analysis', {})
            
            # 速度优化
            optimization = self.api.optimize_speed(ship_data, speed_range=(8, 18), step=2.0)
            
            prediction_result = {
                'case_id': test_case['case_id'],
                'ship_info': {
                    'type': ship_data['船舶类型'],
                    'dwt': ship_data['船舶载重(t)'],
                    'length': ship_data['船舶总长度(m)'],
                    'age': ship_data.get('船龄', 'Unknown')
                },
                'voyage_info': {
                    'speed': ship_data['平均速度(kts)'],
                    'load_condition': ship_data['载重状态'],
                    'distance': ship_data['航行距离(nm)'],
                    'duration': ship_data['航行时间(hrs)']
                },
                'prediction': {
                    'hourly_consumption': result['predicted_fuel_consumption'],
                    'daily_consumption': result['predicted_fuel_consumption'] * 24,
                    'voyage_consumption': result['predicted_fuel_consumption'] * ship_data['航行时间(hrs)'],
                    'confidence': result['confidence'],
                    'method': result.get('method', 'rule_based')
                },
                'cp_analysis': {
                    'warranted_speed': cp_analysis.get('warranted_speed', 'N/A'),
                    'warranted_daily_consumption': cp_analysis.get('warranted_daily_consumption', 'N/A'),
                    'cp_compliance': cp_analysis.get('cp_compliance', False)
                },
                'optimization': {
                    'optimal_speed': optimization.get('optimal_speed', 'N/A'),
                    'savings_potential': optimization.get('savings_potential', 'N/A')
                },
                'recommendations': result.get('recommendations', [])
            }
            
            prediction_results.append(prediction_result)
        
        # 保存预测结果
        results_file = 'outputs/model_predictions.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'system_version': '1.0.0',
                    'total_predictions': len(prediction_results)
                },
                'predictions': prediction_results
            }, f, indent=2, ensure_ascii=False)
        
        # 生成CSV格式的简化结果
        csv_data = []
        for result in prediction_results:
            csv_row = {
                'Case_ID': result['case_id'],
                'Ship_Type': result['ship_info']['type'],
                'DWT': result['ship_info']['dwt'],
                'Speed_kts': result['voyage_info']['speed'],
                'Load_Condition': result['voyage_info']['load_condition'],
                'Predicted_Hourly_Consumption_mt': result['prediction']['hourly_consumption'],
                'Predicted_Daily_Consumption_mt': result['prediction']['daily_consumption'],
                'Confidence': result['prediction']['confidence'],
                'CP_Compliance': result['cp_analysis']['cp_compliance'],
                'Optimal_Speed_kts': result['optimization']['optimal_speed']
            }
            csv_data.append(csv_row)
        
        csv_file = 'outputs/model_predictions.csv'
        pd.DataFrame(csv_data).to_csv(csv_file, index=False, encoding='utf-8')
        
        print(f"✅ 详细预测结果: {results_file}")
        print(f"✅ 简化预测结果: {csv_file}")
        print(f"   预测案例数: {len(prediction_results)}")

def main():
    """主函数"""
    # 创建测试运行器
    test_runner = TestCaseRunner()
    
    # 运行所有测试
    test_report = test_runner.run_all_tests()
    
    # 生成预测结果文件
    test_runner.generate_prediction_results_file()
    
    # 返回测试是否全部通过
    return test_report['summary']['failed'] == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
