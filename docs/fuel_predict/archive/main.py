#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统主程序
一键运行完整的数据分析、模型训练和验证流程

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import os
import sys
import time
import numpy as np
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_analyzer import ShipFuelDataAnalyzer
from src.fuel_prediction_models import MultiShipTypePredictor
from src.model_validation import ModelValidator
from examples.usage_examples import FuelConsumptionPredictor

def print_banner():
    """打印系统横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    船舶油耗预测系统                          ║
    ║              Ship Fuel Consumption Prediction System         ║
    ║                                                              ║
    ║    基于航运行业CP条款和专业知识的智能化油耗预测系统          ║
    ║                                                              ║
    ║    版本: v1.0.0                                              ║
    ║    日期: 2025-09-18                                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_data_file(data_path: str) -> bool:
    """检查数据文件是否存在"""
    if not os.path.exists(data_path):
        print(f"❌ 错误: 数据文件不存在 - {data_path}")
        print("请确保油耗数据文件位于正确位置")
        return False
    
    print(f"✅ 数据文件检查通过 - {data_path}")
    return True

def run_data_analysis(data_path: str):
    """运行数据分析"""
    print("\n" + "="*60)
    print("🔍 第一步: 数据分析")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # 创建分析器
        analyzer = ShipFuelDataAnalyzer(data_path)
        
        # 加载数据
        df = analyzer.load_data()
        
        # 基础统计
        print("\n📊 基础统计信息:")
        stats = analyzer.get_basic_statistics()
        print(f"   数据总量: {stats['数据总量']:,} 条")
        print(f"   船舶数量: {stats['船舶数量']} 艘")
        print(f"   时间范围: {stats['时间范围']['开始时间'].strftime('%Y-%m-%d')} 至 {stats['时间范围']['结束时间'].strftime('%Y-%m-%d')}")
        
        # 船型分布
        print(f"\n🚢 船型分布:")
        for ship_type, count in list(stats['船型分布'].items())[:5]:
            print(f"   {ship_type}: {count:,} 条")
        
        # 船型分析
        ship_analysis = analyzer.analyze_ship_types()
        print(f"\n📈 完成 {len(ship_analysis)} 种船型的详细分析")
        
        # 速度油耗关系
        speed_fuel_corr = analyzer.analyze_speed_fuel_relationship()
        print(f"   分析了 {len(speed_fuel_corr)} 种船型的速度-油耗关系")
        
        # 生成可视化
        print("\n📊 生成可视化图表...")
        fig = analyzer.create_visualization_dashboard('outputs/analysis_dashboard.png')
        print("   ✅ 分析仪表板已保存: outputs/analysis_dashboard.png")
        
        # 生成报告
        report = analyzer.generate_analysis_report()
        with open('reports/analysis_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print("   ✅ 分析报告已保存: reports/analysis_report.md")
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 数据分析完成 (耗时: {elapsed_time:.1f}秒)")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据分析失败: {e}")
        return False

def run_model_training(data_path: str):
    """运行模型训练"""
    print("\n" + "="*60)
    print("🤖 第二步: 模型训练")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # 创建预测系统
        predictor_system = MultiShipTypePredictor()
        
        # 准备数据
        print("📋 准备训练数据...")
        import pandas as pd
        df = pd.read_csv(data_path)
        
        # 计算小时油耗
        df['总油耗(mt)'] = df['重油IFO(mt)'] + df['轻油MDO/MGO(mt)']
        df['小时油耗(mt/h)'] = np.where(
            df['航行时间(hrs)'] > 0,
            df['总油耗(mt)'] / df['航行时间(hrs)'],
            0
        )
        
        X, y = predictor_system.prepare_data(df, target_col='小时油耗(mt/h)')
        
        # 分割数据
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print(f"   训练集: {len(X_train):,} 条")
        print(f"   测试集: {len(X_test):,} 条")
        
        # 训练分船型模型
        print("\n🚢 训练分船型模型...")
        ship_performance = predictor_system.train_ship_type_models(X_train, y_train)
        print(f"   ✅ 成功训练 {len(ship_performance)} 个船型模型")
        
        # 训练全局模型
        print("\n🌐 训练全局模型...")
        global_performance = predictor_system.train_global_model(X_train, y_train)
        print("   ✅ 全局模型训练完成")
        
        # 模型评估
        print("\n📊 评估模型性能...")
        evaluation_results = predictor_system.evaluate_models(X_test, y_test)
        
        overall_metrics = evaluation_results.get('Overall', {})
        if overall_metrics:
            print(f"   整体性能:")
            print(f"     MAE: {overall_metrics.get('MAE', 0):.3f} mt/h")
            print(f"     RMSE: {overall_metrics.get('RMSE', 0):.3f} mt/h")
            print(f"     R²: {overall_metrics.get('R2', 0):.3f}")
            print(f"     MAPE: {overall_metrics.get('MAPE', 0):.1f}%")
        
        # 保存模型
        print("\n💾 保存模型...")
        model_save_path = 'models/fuel_prediction_models.pkl'
        predictor_system.save_models(model_save_path)
        print(f"   ✅ 模型已保存: {model_save_path}")
        
        # 生成模型报告
        report = predictor_system.generate_model_report()
        with open('reports/model_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print("   ✅ 模型报告已保存: reports/model_report.md")
        
        # 保存评估结果
        import json
        with open('outputs/evaluation_results.json', 'w', encoding='utf-8') as f:
            json.dump(evaluation_results, f, indent=2, ensure_ascii=False)
        print("   ✅ 评估结果已保存: outputs/evaluation_results.json")
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 模型训练完成 (耗时: {elapsed_time:.1f}秒)")
        
        return predictor_system, X_test, y_test, X_train, y_train
        
    except Exception as e:
        print(f"❌ 模型训练失败: {e}")
        return None, None, None, None, None

def run_model_validation(predictor_system, X_test, y_test, X_train, y_train):
    """运行模型验证"""
    print("\n" + "="*60)
    print("✅ 第三步: 模型验证")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # 创建验证器
        validator = ModelValidator(predictor_system)
        
        # 综合验证
        print("🔍 执行综合验证...")
        validation_results = validator.comprehensive_validation(
            X_test, y_test, X_train, y_train
        )
        
        # 显示验证结果
        if 'basic_metrics' in validation_results:
            metrics = validation_results['basic_metrics']
            print(f"\n📊 验证结果:")
            print(f"   MAE: {metrics.get('MAE', 0):.3f} mt/h")
            print(f"   RMSE: {metrics.get('RMSE', 0):.3f} mt/h")
            print(f"   R²: {metrics.get('R2', 0):.3f}")
            print(f"   MAPE: {metrics.get('MAPE', 0):.1f}%")
        
        # 分船型验证结果
        if 'ship_type_analysis' in validation_results:
            ship_analysis = validation_results['ship_type_analysis']
            print(f"\n🚢 分船型验证 ({len(ship_analysis)} 个船型):")
            for ship_type, metrics in list(ship_analysis.items())[:3]:
                print(f"   {ship_type}:")
                print(f"     样本: {metrics.get('sample_count', 0)}")
                print(f"     R²: {metrics.get('R2', 0):.3f}")
                print(f"     MAPE: {metrics.get('MAPE', 0):.1f}%")
        
        # 生成验证报告
        print("\n📝 生成验证报告...")
        report = validator.generate_validation_report()
        with open('reports/validation_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print("   ✅ 验证报告已保存: reports/validation_report.md")
        
        # 生成验证可视化
        print("📊 生成验证可视化...")
        fig = validator.create_validation_visualizations(
            X_test, y_test, 'outputs/validation_dashboard.png'
        )
        print("   ✅ 验证仪表板已保存: outputs/validation_dashboard.png")
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 模型验证完成 (耗时: {elapsed_time:.1f}秒)")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型验证失败: {e}")
        return False

def run_usage_demo():
    """运行使用演示"""
    print("\n" + "="*60)
    print("🎯 第四步: 使用演示")
    print("="*60)
    
    try:
        # 创建API预测器
        predictor = FuelConsumptionPredictor('models/fuel_prediction_models.pkl')
        
        # 单次航行预测演示
        print("\n🚢 单次航行预测演示:")
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
        
        result = predictor.predict_single_voyage(voyage_data)
        print(f"   预测小时油耗: {result['predicted_fuel_consumption']:.2f} mt/h")
        print(f"   置信度: {result['confidence_level']}")
        print(f"   CP条款合规: {result['cp_clause_analysis']['cp_compliance']}")
        
        # 速度优化演示
        print("\n⚡ 速度优化演示:")
        optimization_result = predictor.optimize_speed_for_fuel(
            voyage_data, speed_range=(10, 16), step=1.0
        )
        
        if 'optimal_speed' in optimization_result:
            print(f"   最优速度: {optimization_result['optimal_speed']:.1f} kts")
            print(f"   节省燃料: {optimization_result.get('fuel_savings', 0):.1f} mt")
        
        print("\n✅ 使用演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 使用演示失败: {e}")
        print("   提示: 请确保模型已正确训练和保存")
        return False

def generate_summary():
    """生成总结报告"""
    print("\n" + "="*60)
    print("📋 系统运行总结")
    print("="*60)
    
    # 检查生成的文件
    generated_files = [
        'analysis_dashboard.png',
        'analysis_report.md',
        'fuel_prediction_models.pkl',
        'model_report.md',
        'evaluation_results.json',
        'validation_report.md',
        'validation_dashboard.png'
    ]
    
    print("\n📁 生成的文件:")
    for file_name in generated_files:
        if os.path.exists(file_name):
            file_size = os.path.getsize(file_name)
            if file_size > 1024*1024:
                size_str = f"{file_size/(1024*1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size/1024:.1f} KB"
            else:
                size_str = f"{file_size} B"
            print(f"   ✅ {file_name} ({size_str})")
        else:
            print(f"   ❌ {file_name} (未生成)")
    
    print(f"\n🎯 系统特性:")
    print(f"   ✅ 多船型专业预测模型")
    print(f"   ✅ CP条款合规性分析")
    print(f"   ✅ 智能特征工程")
    print(f"   ✅ 综合模型验证")
    print(f"   ✅ 速度优化功能")
    print(f"   ✅ 可视化分析仪表板")
    
    print(f"\n📚 使用方法:")
    print(f"   1. 查看分析报告: analysis_report.md")
    print(f"   2. 查看模型性能: model_report.md")
    print(f"   3. 查看验证结果: validation_report.md")
    print(f"   4. 使用预测API: from usage_examples import FuelConsumptionPredictor")
    print(f"   5. 运行完整演示: python usage_examples.py")

def main():
    """主函数"""
    print_banner()
    
    # 记录开始时间
    total_start_time = time.time()
    
    # 数据文件路径
    data_path = 'data/油耗数据ALL（0804）.csv'
    
    # 检查数据文件
    if not check_data_file(data_path):
        return
    
    print(f"\n🚀 开始运行船舶油耗预测系统")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success_count = 0
    total_steps = 4
    
    # 第一步: 数据分析
    if run_data_analysis(data_path):
        success_count += 1
    
    # 第二步: 模型训练
    predictor_system, X_test, y_test, X_train, y_train = run_model_training(data_path)
    if predictor_system is not None:
        success_count += 1
        
        # 第三步: 模型验证
        if run_model_validation(predictor_system, X_test, y_test, X_train, y_train):
            success_count += 1
        
        # 第四步: 使用演示
        if run_usage_demo():
            success_count += 1
    
    # 总结
    total_elapsed = time.time() - total_start_time
    
    print(f"\n" + "="*60)
    print(f"🏁 系统运行完成")
    print(f"="*60)
    print(f"⏱️  总耗时: {total_elapsed:.1f} 秒")
    print(f"✅ 成功步骤: {success_count}/{total_steps}")
    print(f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success_count == total_steps:
        print(f"\n🎉 恭喜！船舶油耗预测系统已完全构建成功！")
        generate_summary()
    else:
        print(f"\n⚠️  系统构建部分完成，请检查错误信息并重试")
    
    print(f"\n" + "="*60)

if __name__ == "__main__":
    main()
