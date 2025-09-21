#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格预测器 - 使用训练好的模型进行预测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class PricePredictor:
    """价格预测器"""
    
    def __init__(self, model_factory, scalers):
        self.model_factory = model_factory
        self.scalers = scalers
        self.feature_columns = []
        
    def set_feature_columns(self, feature_columns):
        """设置特征列"""
        self.feature_columns = feature_columns
    
    def predict_single(self, X, model_name, horizon='1d'):
        """单模型预测"""
        if model_name not in self.model_factory.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        model = self.model_factory.models[model_name]
        
        if horizon in ['1d', '7d', '30d']:
            # 使用对应时间跨度的模型
            horizon_model_name = f"{model_name}_{horizon}"
            if horizon_model_name in self.model_factory.models:
                model = self.model_factory.models[horizon_model_name]
        
        # 数据标准化
        if model_name in self.scalers:
            X_scaled = self.scalers[model_name].transform(X)
        else:
            X_scaled = X
        
        # 预测
        if hasattr(model, 'predict'):
            predictions = model.predict(X_scaled)
        elif hasattr(model, 'forecast'):
            predictions = model.forecast(len(X))
        else:
            raise ValueError(f"模型 {model_name} 不支持预测")
        
        return predictions
    
    def predict_ensemble(self, X, horizon='1d', weights=None):
        """集成预测"""
        if weights is None:
            # 默认权重（基于模型性能）
            weights = {
                'Ridge': 0.4,
                'RandomForest': 0.3,
                'GradientBoosting': 0.2,
                'XGBoost': 0.1
            }
        
        predictions = {}
        ensemble_pred = np.zeros(len(X))
        total_weight = 0
        
        for model_name, weight in weights.items():
            if model_name in self.model_factory.models:
                try:
                    pred = self.predict_single(X, model_name, horizon)
                    predictions[model_name] = pred
                    ensemble_pred += weight * pred
                    total_weight += weight
                except Exception as e:
                    print(f"模型 {model_name} 预测失败: {e}")
        
        if total_weight > 0:
            ensemble_pred /= total_weight
        
        return ensemble_pred, predictions
    
    def predict_future(self, X, horizon='1d', days=7, method='ensemble'):
        """预测未来价格"""
        if method == 'ensemble':
            predictions, individual_preds = self.predict_ensemble(X, horizon)
        else:
            predictions = self.predict_single(X, method, horizon)
            individual_preds = {method: predictions}
        
        # 创建预测结果DataFrame
        future_dates = pd.date_range(
            start=datetime.now() + timedelta(days=1),
            periods=days,
            freq='D'
        )
        
        # 确保所有数组长度一致
        min_length = min(len(future_dates), len(predictions))
        future_dates = future_dates[:min_length]
        predictions = predictions[:min_length]
        
        result_df = pd.DataFrame({
            'Date': future_dates,
            'Prediction': predictions
        })
        
        # 添加各个模型的预测
        for model_name, pred in individual_preds.items():
            pred_trimmed = pred[:min_length] if len(pred) > min_length else pred
            result_df[f'{model_name}_Prediction'] = pred_trimmed
        
        # 计算预测区间
        if len(individual_preds) > 1:
            pred_values = list(individual_preds.values())
            pred_std = np.std(pred_values, axis=0)
            pred_std = pred_std[:min_length] if len(pred_std) > min_length else pred_std
            result_df['Upper_Bound'] = predictions + 1.96 * pred_std
            result_df['Lower_Bound'] = predictions - 1.96 * pred_std
        else:
            # 使用历史误差估计
            result_df['Upper_Bound'] = predictions * 1.1
            result_df['Lower_Bound'] = predictions * 0.9
        
        return result_df
    
    def get_prediction_summary(self, predictions_df):
        """获取预测摘要"""
        current_price = predictions_df['Prediction'].iloc[0]
        future_price = predictions_df['Prediction'].iloc[-1]
        price_change = future_price - current_price
        change_rate = (price_change / current_price) * 100
        
        return {
            'current_price': current_price,
            'future_price': future_price,
            'price_change': price_change,
            'change_rate': change_rate,
            'trend': '上涨' if price_change > 0 else '下跌',
            'confidence': '高' if abs(change_rate) < 5 else '中' if abs(change_rate) < 10 else '低'
        }
    
    def create_prediction_visualization(self, predictions_df, historical_data=None, save_path='prediction/price_predictions.png'):
        """创建预测可视化"""
        import matplotlib.pyplot as plt
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # 绘制历史数据
        if historical_data is not None:
            ax.plot(historical_data['Date'], historical_data['Price_Mean'], 
                   label='历史价格', color='blue', linewidth=2)
        
        # 绘制预测数据
        ax.plot(predictions_df['Date'], predictions_df['Prediction'], 
               label='预测价格', color='red', linewidth=2, linestyle='--')
        
        # 绘制预测区间
        if 'Upper_Bound' in predictions_df.columns:
            ax.fill_between(predictions_df['Date'], 
                           predictions_df['Lower_Bound'], 
                           predictions_df['Upper_Bound'], 
                           alpha=0.3, color='red', label='95%置信区间')
        
        # 绘制各个模型的预测
        for col in predictions_df.columns:
            if col.endswith('_Prediction') and col != 'Prediction':
                model_name = col.replace('_Prediction', '')
                ax.plot(predictions_df['Date'], predictions_df[col], 
                       label=f'{model_name}预测', alpha=0.7, linewidth=1)
        
        ax.set_title('FFA价格预测结果', fontsize=16, fontweight='bold')
        ax.set_xlabel('日期')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"预测可视化图已保存到: {save_path}")
    
    def save_predictions(self, predictions_df, save_path='prediction/ffa_predictions.csv'):
        """保存预测结果"""
        predictions_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"预测结果已保存到: {save_path}")
    
    def generate_prediction_report(self, predictions_df, save_path='prediction/prediction_report.txt'):
        """生成预测报告"""
        summary = self.get_prediction_summary(predictions_df)
        
        report = []
        report.append("=" * 60)
        report.append("FFA价格预测报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 预测摘要
        report.append("预测摘要:")
        report.append("-" * 30)
        report.append(f"当前价格: {summary['current_price']:.2f}")
        report.append(f"未来价格: {summary['future_price']:.2f}")
        report.append(f"价格变化: {summary['price_change']:.2f}")
        report.append(f"变化率: {summary['change_rate']:.2f}%")
        report.append(f"趋势: {summary['trend']}")
        report.append(f"置信度: {summary['confidence']}")
        report.append("")
        
        # 详细预测
        report.append("详细预测:")
        report.append("-" * 30)
        for _, row in predictions_df.iterrows():
            report.append(f"{row['Date'].strftime('%Y-%m-%d')}: {row['Prediction']:.2f}")
        
        # 保存报告
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"预测报告已保存到: {save_path}")
        
        # 打印到控制台
        print('\n'.join(report))
