#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA价格预测系统主程序 - 专门为FFA市场设计
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

from data.market_data_processor import FFAMarketDataProcessor
from models.ffa_model_factory import FFAModelFactory
from evaluation.model_evaluator import ModelEvaluator
from prediction.ffa_predictor import FFAPredictor
from config.model_config import FFA_CONFIG

def create_directories():
    """创建必要的目录"""
    directories = ['data', 'models', 'evaluation', 'prediction', 'results', 'config']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def main():
    """主函数"""
    print("=" * 80)
    print("FFA价格预测系统 - 专业版")
    print("=" * 80)
    
    # 创建目录
    create_directories()
    
    # 1. 数据处理
    print("\n1. FFA市场数据处理阶段")
    print("-" * 40)
    data_processor = FFAMarketDataProcessor()
    daily_features = data_processor.process_all_ffa_data("FFA - tradetape - EEX.xlsx")
    
    # 2. 模型训练
    print("\n2. FFA模型训练阶段")
    print("-" * 40)
    
    # 准备特征和目标变量
    feature_cols = [col for col in daily_features.columns if col not in ['Date', 'Price_Mean']]
    X = daily_features[feature_cols]
    
    # 训练不同时间跨度的模型
    horizon_types = ['short_term', 'medium_term', 'long_term']
    all_models = {}
    all_scalers = {}
    
    for horizon_type in horizon_types:
        print(f"\n训练{horizon_type}模型...")
        
        # 选择目标变量
        if horizon_type == 'short_term':
            target_cols = ['Price_Future_1d', 'Price_Future_3d', 'Price_Future_7d']
        elif horizon_type == 'medium_term':
            target_cols = ['Price_Future_14d', 'Price_Future_30d', 'Price_Future_60d']
        else:
            target_cols = ['Price_Future_90d', 'Price_Future_180d', 'Price_Future_365d']
        
        # 训练每个目标变量
        for target_col in target_cols:
            if target_col in daily_features.columns:
                print(f"  训练{target_col}模型...")
                
                y = daily_features[target_col]
                
                # 分割数据
                from sklearn.model_selection import train_test_split
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, shuffle=False
                )
                
                # 创建模型工厂
                model_factory = FFAModelFactory()
                
                # 训练模型
                model_results = model_factory.train_ffa_models(
                    X_train, X_test, y_train, y_test, horizon_type
                )
                
                # 选择最佳模型
                best_models = model_factory.select_best_ffa_models('rmse', horizon_type)
                
                # 保存最佳模型
                for model_name, score in best_models.items():
                    if score is not None:
                        all_models[f"{model_name}_{target_col}"] = model_factory.get_model(model_name)
                        scaler = model_factory.get_scaler(model_name)
                        if scaler is not None:
                            all_scalers[f"{model_name}_{target_col}"] = scaler
    
    # 3. 模型评估
    print("\n3. FFA模型评估阶段")
    print("-" * 40)
    
    # 评估短期模型
    print("评估短期模型...")
    short_term_models = {k: v for k, v in all_models.items() if '1d' in k or '3d' in k or '7d' in k}
    
    if short_term_models:
        # 使用1天预测进行评估
        y_1d = daily_features['Price_Future_1d']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_1d, test_size=0.2, random_state=42, shuffle=False
        )
        
        evaluator = ModelEvaluator()
        evaluation_results = evaluator.evaluate_models(short_term_models, X_test, y_test)
        
        # 创建评估可视化
        evaluator.create_performance_comparison('evaluation/ffa_performance_comparison.png')
        
        # 创建预测对比图
        model_predictions = {}
        for name, result in evaluation_results.items():
            if result is not None:
                model_predictions[name] = result['predictions']
        
        if model_predictions:
            evaluator.create_prediction_comparison(y_test, model_predictions, 
                                                 'evaluation/ffa_prediction_comparison.png')
    
    # 4. FFA价格预测
    print("\n4. FFA价格预测阶段")
    print("-" * 40)
    
    # 创建FFA预测器
    ffa_model_factory = FFAModelFactory()
    ffa_model_factory.models = all_models
    ffa_model_factory.scalers = all_scalers
    
    ffa_predictor = FFAPredictor(ffa_model_factory)
    ffa_predictor.set_feature_columns(feature_cols)
    
    # 预测不同产品
    products = FFA_CONFIG['target_products']
    
    for product in products:
        print(f"\n预测{product}价格...")
        
        # 短期预测
        predictions_short, multi_horizon_short = ffa_predictor.predict_future_prices(
            X, 'short_term', 7, product
        )
        
        # 中期预测
        predictions_medium, multi_horizon_medium = ffa_predictor.predict_future_prices(
            X, 'medium_term', 30, product
        )
        
        # 长期预测
        predictions_long, multi_horizon_long = ffa_predictor.predict_future_prices(
            X, 'long_term', 90, product
        )
        
        # 保存预测结果
        ffa_predictor.save_ffa_predictions(predictions_short, f'prediction/{product}_short_term.csv')
        ffa_predictor.save_ffa_predictions(predictions_medium, f'prediction/{product}_medium_term.csv')
        ffa_predictor.save_ffa_predictions(predictions_long, f'prediction/{product}_long_term.csv')
        
        # 创建可视化
        ffa_predictor.create_ffa_visualization(predictions_short, daily_features, 
                                             f'prediction/{product}_short_term.png')
        
        # 生成报告
        ffa_predictor.generate_ffa_report(predictions_short, multi_horizon_short, 
                                        f'prediction/{product}_report.txt')
    
    # 5. 结果总结
    print("\n5. FFA预测结果总结")
    print("-" * 40)
    
    # 显示预测结果
    print("\nFFA价格预测结果:")
    for product in products:
        print(f"\n{product}短期预测 (未来7天):")
        predictions_file = f'prediction/{product}_short_term.csv'
        if os.path.exists(predictions_file):
            predictions_df = pd.read_csv(predictions_file)
            print(predictions_df[['Date', 'Prediction']].to_string(index=False))
            
            # 显示预测摘要
            summary = ffa_predictor.get_prediction_summary(predictions_df, product)
            print(f"\n{product}预测摘要:")
            print(f"  当前价格: {summary['current_price']:,.2f}")
            print(f"  未来价格: {summary['future_price']:,.2f}")
            print(f"  价格变化: {summary['price_change']:,.2f}")
            print(f"  变化率: {summary['change_rate']:.2f}%")
            print(f"  趋势: {summary['trend']}")
            print(f"  置信度: {summary['confidence']}")
            print(f"  波动率: {summary['volatility']:.2f}%")
    
    # 6. 生成最终报告
    generate_final_ffa_report(products, daily_features)

def generate_final_ffa_report(products, daily_features):
    """生成最终FFA报告"""
    print("\n正在生成最终FFA报告...")
    
    report = []
    report.append("=" * 80)
    report.append("FFA价格预测系统 - 最终报告")
    report.append("=" * 80)
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 数据概况
    report.append("数据概况:")
    report.append("-" * 40)
    report.append(f"数据时间范围: {daily_features['Date'].min()} 至 {daily_features['Date'].max()}")
    report.append(f"数据点数量: {len(daily_features)}")
    report.append(f"特征数量: {daily_features.shape[1] - 1}")
    report.append("")
    
    # 产品预测
    report.append("产品预测结果:")
    report.append("-" * 40)
    
    for product in products:
        predictions_file = f'prediction/{product}_short_term.csv'
        if os.path.exists(predictions_file):
            predictions_df = pd.read_csv(predictions_file)
            current_price = predictions_df['Prediction'].iloc[0]
            future_price = predictions_df['Prediction'].iloc[-1]
            change_rate = (future_price - current_price) / current_price * 100
            
            report.append(f"\n{product}:")
            report.append(f"  当前价格: {current_price:,.2f}")
            report.append(f"  未来价格: {future_price:,.2f}")
            report.append(f"  变化率: {change_rate:.2f}%")
            report.append(f"  趋势: {'上涨' if change_rate > 0 else '下跌'}")
    
    # 市场分析
    report.append(f"\n市场分析:")
    report.append("-" * 40)
    report.append("基于FFA市场特性，本系统考虑了以下因素：")
    report.append("1. 商品价格影响：原油、铁矿石、煤炭等大宗商品价格")
    report.append("2. 宏观经济因素：GDP、PMI、利率、汇率等")
    report.append("3. 航运市场因素：船舶数量、港口拥堵、船队利用率等")
    report.append("4. 天气因素：风速、波高、风暴指数等")
    report.append("5. AIS数据：船舶速度、密度、航线拥堵等")
    report.append("6. 技术指标：RSI、MACD、布林带、移动平均等")
    
    # 保存报告
    with open('results/final_ffa_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print("最终FFA报告已保存到: results/final_ffa_report.txt")

if __name__ == "__main__":
    main()
