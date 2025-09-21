#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA价格预测系统主程序
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_processor import DataProcessor
from models.model_factory import ModelFactory
from evaluation.model_evaluator import ModelEvaluator
from prediction.price_predictor import PricePredictor

def create_directories():
    """创建必要的目录"""
    directories = ['data', 'models', 'evaluation', 'prediction', 'results']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def main():
    """主函数"""
    print("=" * 80)
    print("FFA价格预测系统 - 完整流程")
    print("=" * 80)
    
    # 创建目录
    create_directories()
    
    # 1. 数据处理
    print("\n1. 数据处理阶段")
    print("-" * 40)
    data_processor = DataProcessor()
    X, y_1d, y_7d, y_30d, daily_features = data_processor.process_all("FFA - tradetape - EEX.xlsx")
    
    # 2. 模型训练
    print("\n2. 模型训练阶段")
    print("-" * 40)
    model_factory = ModelFactory()
    
    # 分割数据
    from sklearn.model_selection import train_test_split
    
    # 训练不同时间跨度的模型
    time_horizons = {
        '1d': y_1d,
        '7d': y_7d,
        '30d': y_30d
    }
    
    all_models = {}
    all_scalers = {}
    
    for horizon, y in time_horizons.items():
        print(f"\n训练{horizon}预测模型...")
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # 训练模型
        model_results = model_factory.train_models(X_train, X_test, y_train, y_test)
        
        # 选择最佳模型
        best_models = model_factory.select_best_models('rmse')
        
        # 保存最佳模型
        for model_name, score in best_models.items():
            if score is not None:
                all_models[f"{model_name}_{horizon}"] = model_factory.get_model(model_name)
                scaler = model_factory.get_scaler(model_name)
                if scaler is not None:
                    all_scalers[f"{model_name}_{horizon}"] = scaler
    
    # 3. 模型评估
    print("\n3. 模型评估阶段")
    print("-" * 40)
    evaluator = ModelEvaluator()
    
    # 评估所有模型
    evaluation_results = {}
    for horizon, y in time_horizons.items():
        print(f"\n评估{horizon}预测模型...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # 获取该时间跨度的模型
        horizon_models = {k: v for k, v in all_models.items() if k.endswith(f'_{horizon}')}
        
        if horizon_models:
            results = evaluator.evaluate_models(horizon_models, X_test, y_test)
            evaluation_results[horizon] = results
    
    # 创建评估可视化
    print("\n正在创建评估可视化...")
    evaluator.create_performance_comparison('evaluation/performance_comparison.png')
    
    # 创建预测对比图
    if evaluation_results:
        # 使用1天预测的模型进行对比
        if '1d' in evaluation_results:
            model_predictions = {}
            for name, result in evaluation_results['1d'].items():
                if result is not None:
                    model_predictions[name] = result['predictions']
            
            if model_predictions:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y_1d, test_size=0.2, random_state=42, shuffle=False
                )
                evaluator.create_prediction_comparison(y_test, model_predictions, 
                                                     'evaluation/prediction_comparison.png')
    
    # 4. 价格预测
    print("\n4. 价格预测阶段")
    print("-" * 40)
    
    # 创建预测器
    predictor = PricePredictor(model_factory, all_scalers)
    predictor.set_feature_columns(data_processor.feature_columns)
    
    # 生成预测
    print("正在生成价格预测...")
    
    # 预测未来7天
    predictions_1d = predictor.predict_future(X, '1d', 7, 'ensemble')
    predictions_7d = predictor.predict_future(X, '7d', 7, 'ensemble')
    predictions_30d = predictor.predict_future(X, '30d', 7, 'ensemble')
    
    # 保存预测结果
    predictor.save_predictions(predictions_1d, 'prediction/predictions_1d.csv')
    predictor.save_predictions(predictions_7d, 'prediction/predictions_7d.csv')
    predictor.save_predictions(predictions_30d, 'prediction/predictions_30d.csv')
    
    # 创建预测可视化
    predictor.create_prediction_visualization(predictions_1d, daily_features, 
                                            'prediction/price_predictions_1d.png')
    
    # 生成预测报告
    predictor.generate_prediction_report(predictions_1d, 'prediction/prediction_report_1d.txt')
    
    # 5. 结果总结
    print("\n5. 结果总结")
    print("-" * 40)
    
    # 显示预测结果
    print("\n未来7天价格预测 (1天模型):")
    print(predictions_1d[['Date', 'Prediction']].to_string(index=False))
    
    # 显示预测摘要
    summary = predictor.get_prediction_summary(predictions_1d)
    print(f"\n预测摘要:")
    print(f"  当前价格: {summary['current_price']:.2f}")
    print(f"  未来价格: {summary['future_price']:.2f}")
    print(f"  价格变化: {summary['price_change']:.2f}")
    print(f"  变化率: {summary['change_rate']:.2f}%")
    print(f"  趋势: {summary['trend']}")
    print(f"  置信度: {summary['confidence']}")
    
    # 显示最佳模型
    print(f"\n最佳模型:")
    for horizon, results in evaluation_results.items():
        if results:
            best_model = min(results.items(), key=lambda x: x[1]['metrics']['rmse'] if x[1] else float('inf'))
            if best_model[1]:
                print(f"  {horizon}预测: {best_model[0]} (RMSE: {best_model[1]['metrics']['rmse']:.2f})")
    
    print(f"\n✅ 预测完成！所有结果已保存到相应目录中。")
    
    # 6. 生成最终报告
    generate_final_report(evaluation_results, predictions_1d)

def generate_final_report(evaluation_results, predictions_1d):
    """生成最终报告"""
    print("\n正在生成最终报告...")
    
    report = []
    report.append("=" * 80)
    report.append("FFA价格预测系统 - 最终报告")
    report.append("=" * 80)
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 模型性能总结
    report.append("模型性能总结:")
    report.append("-" * 40)
    
    for horizon, results in evaluation_results.items():
        if results:
            report.append(f"\n{horizon}预测:")
            best_model = min(results.items(), key=lambda x: x[1]['metrics']['rmse'] if x[1] else float('inf'))
            if best_model[1]:
                metrics = best_model[1]['metrics']
                report.append(f"  最佳模型: {best_model[0]}")
                report.append(f"  RMSE: {metrics['rmse']:.2f}")
                report.append(f"  R²: {metrics['r2']:.3f}")
                report.append(f"  MAPE: {metrics['mape']:.2f}%")
                report.append(f"  方向准确率: {metrics['direction_accuracy']:.2f}%")
    
    # 预测结果
    report.append(f"\n预测结果:")
    report.append("-" * 40)
    
    current_price = predictions_1d['Prediction'].iloc[0]
    future_price = predictions_1d['Prediction'].iloc[-1]
    price_change = future_price - current_price
    change_rate = (price_change / current_price) * 100
    
    report.append(f"当前价格: {current_price:.2f}")
    report.append(f"未来价格: {future_price:.2f}")
    report.append(f"价格变化: {price_change:.2f}")
    report.append(f"变化率: {change_rate:.2f}%")
    report.append(f"趋势: {'上涨' if price_change > 0 else '下跌'}")
    
    # 详细预测
    report.append(f"\n详细预测:")
    report.append("-" * 40)
    for _, row in predictions_1d.iterrows():
        report.append(f"{row['Date'].strftime('%Y-%m-%d')}: {row['Prediction']:.2f}")
    
    # 保存报告
    with open('results/final_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print("最终报告已保存到: results/final_report.txt")

if __name__ == "__main__":
    main()