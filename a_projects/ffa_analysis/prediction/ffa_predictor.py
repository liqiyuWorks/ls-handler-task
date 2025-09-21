#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA预测器 - 专门为FFA市场设计的预测器
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config.model_config import FFA_CONFIG, PREDICTION_CONFIG

class FFAPredictor:
    """FFA预测器"""
    
    def __init__(self, model_factory):
        self.model_factory = model_factory
        self.config = FFA_CONFIG
        self.prediction_config = PREDICTION_CONFIG
        self.feature_columns = []
        
    def set_feature_columns(self, feature_columns):
        """设置特征列"""
        self.feature_columns = feature_columns
    
    def predict_single_horizon(self, X, model_name, horizon_days):
        """单模型单时间跨度预测"""
        if model_name not in self.model_factory.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        model = self.model_factory.models[model_name]
        scaler = self.model_factory.get_scaler(model_name)
        
        # 数据标准化
        if scaler is not None:
            X_scaled = scaler.transform(X)
        else:
            X_scaled = X
        
        # 预测
        if hasattr(model, 'predict'):
            predictions = model.predict(X_scaled)
        elif hasattr(model, 'forecast'):
            predictions = model.forecast(horizon_days)
        else:
            raise ValueError(f"模型 {model_name} 不支持预测")
        
        return predictions
    
    def predict_ensemble_horizon(self, X, ensemble_models, horizon_days):
        """集成模型单时间跨度预测"""
        predictions = {}
        ensemble_pred = np.zeros(horizon_days)
        total_weight = 0
        
        for model_name, model_info in ensemble_models.items():
            model = model_info['model']
            weight = model_info['weight']
            scaler = model_info['scaler']
            
            try:
                if scaler is not None:
                    X_scaled = scaler.transform(X)
                    pred = model.predict(X_scaled)
                else:
                    pred = model.predict(X)
                
                # 确保预测长度正确
                if len(pred) > horizon_days:
                    pred = pred[:horizon_days]
                elif len(pred) < horizon_days:
                    pred = np.pad(pred, (0, horizon_days - len(pred)), mode='edge')
                
                predictions[model_name] = pred
                ensemble_pred += weight * pred
                total_weight += weight
                
            except Exception as e:
                print(f"模型 {model_name} 预测失败: {e}")
        
        if total_weight > 0:
            ensemble_pred /= total_weight
        
        return ensemble_pred, predictions
    
    def predict_multi_horizon(self, X, horizon_type='short_term', days=7):
        """多时间跨度预测"""
        print(f"正在生成{horizon_type}多时间跨度预测...")
        
        # 获取时间跨度配置
        if horizon_type == 'short_term':
            horizons = self.config['time_horizons']['short_term']
        elif horizon_type == 'medium_term':
            horizons = self.config['time_horizons']['medium_term']
        elif horizon_type == 'long_term':
            horizons = self.config['time_horizons']['long_term']
        else:
            horizons = [1, 7, 30]
        
        # 创建集成模型
        ensemble_models = self.model_factory.create_ensemble_model(horizon_type)
        
        # 预测结果
        predictions = {}
        
        for horizon in horizons:
            if horizon <= days:
                print(f"预测{horizon}天...")
                
                # 使用集成模型预测
                ensemble_pred, individual_preds = self.predict_ensemble_horizon(
                    X, ensemble_models, horizon
                )
                
                predictions[f'{horizon}d'] = {
                    'ensemble': ensemble_pred,
                    'individual': individual_preds
                }
        
        return predictions
    
    def predict_future_prices(self, X, horizon_type='short_term', days=7, product='P4TC'):
        """预测未来价格"""
        print(f"正在预测{product}未来{days}天价格...")
        
        # 多时间跨度预测
        multi_horizon_preds = self.predict_multi_horizon(X, horizon_type, days)
        
        # 创建预测结果DataFrame
        future_dates = pd.date_range(
            start=datetime.now() + timedelta(days=1),
            periods=days,
            freq='D'
        )
        
        # 选择最佳时间跨度的预测
        best_horizon = min([h for h in multi_horizon_preds.keys()], key=lambda x: int(x.replace('d', '')))
        best_pred = multi_horizon_preds[best_horizon]
        
        # 确保数组长度一致
        min_length = min(len(future_dates), len(best_pred['ensemble']), days)
        future_dates = future_dates[:min_length]
        ensemble_pred = best_pred['ensemble'][:min_length]
        
        # 创建结果DataFrame
        result_df = pd.DataFrame({
            'Date': future_dates,
            'Product': product,
            'Prediction': ensemble_pred
        })
        
        # 添加各个模型的预测
        for model_name, pred in best_pred['individual'].items():
            pred_trimmed = pred[:min_length] if len(pred) > min_length else pred
            result_df[f'{model_name}_Prediction'] = pred_trimmed
        
        # 计算预测区间
        if len(best_pred['individual']) > 1:
            pred_values = list(best_pred['individual'].values())
            pred_std = np.std(pred_values, axis=0)
            pred_std = pred_std[:min_length] if len(pred_std) > min_length else pred_std
            
            for confidence in self.prediction_config['confidence_levels']:
                z_score = {0.68: 1, 0.95: 1.96, 0.99: 2.58}[confidence]
                result_df[f'Upper_Bound_{int(confidence*100)}'] = result_df['Prediction'] + z_score * pred_std
                result_df[f'Lower_Bound_{int(confidence*100)}'] = result_df['Prediction'] - z_score * pred_std
        else:
            # 使用历史误差估计
            for confidence in self.prediction_config['confidence_levels']:
                z_score = {0.68: 1, 0.95: 1.96, 0.99: 2.58}[confidence]
                result_df[f'Upper_Bound_{int(confidence*100)}'] = result_df['Prediction'] * (1 + z_score * 0.1)
                result_df[f'Lower_Bound_{int(confidence*100)}'] = result_df['Prediction'] * (1 - z_score * 0.1)
        
        return result_df, multi_horizon_preds
    
    def get_prediction_summary(self, predictions_df, product='P4TC'):
        """获取预测摘要"""
        current_price = predictions_df['Prediction'].iloc[0]
        future_price = predictions_df['Prediction'].iloc[-1]
        price_change = future_price - current_price
        change_rate = (price_change / current_price) * 100
        
        # 计算趋势
        if change_rate > 5:
            trend = '强势上涨'
        elif change_rate > 1:
            trend = '上涨'
        elif change_rate > -1:
            trend = '震荡'
        elif change_rate > -5:
            trend = '下跌'
        else:
            trend = '强势下跌'
        
        # 计算置信度
        if abs(change_rate) < 2:
            confidence = '高'
        elif abs(change_rate) < 5:
            confidence = '中'
        else:
            confidence = '低'
        
        # 计算波动率
        volatility = predictions_df['Prediction'].std() / predictions_df['Prediction'].mean() * 100
        
        return {
            'product': product,
            'current_price': current_price,
            'future_price': future_price,
            'price_change': price_change,
            'change_rate': change_rate,
            'trend': trend,
            'confidence': confidence,
            'volatility': volatility
        }
    
    def create_ffa_visualization(self, predictions_df, historical_data=None, 
                                save_path='prediction/ffa_predictions.png'):
        """创建FFA预测可视化"""
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('FFA价格预测分析', fontsize=16, fontweight='bold')
        
        # 1. 价格趋势图
        ax1 = axes[0, 0]
        
        # 绘制历史数据
        if historical_data is not None:
            ax1.plot(historical_data['Date'], historical_data['Price_Mean'], 
                    label='历史价格', color='blue', linewidth=2)
        
        # 绘制预测数据
        ax1.plot(predictions_df['Date'], predictions_df['Prediction'], 
                label='预测价格', color='red', linewidth=2, linestyle='--')
        
        # 绘制置信区间
        if 'Upper_Bound_95' in predictions_df.columns:
            ax1.fill_between(predictions_df['Date'], 
                           predictions_df['Lower_Bound_95'], 
                           predictions_df['Upper_Bound_95'], 
                           alpha=0.3, color='red', label='95%置信区间')
        
        ax1.set_title('价格趋势预测')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('价格')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 预测分布图
        ax2 = axes[0, 1]
        ax2.hist(predictions_df['Prediction'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.axvline(predictions_df['Prediction'].mean(), color='red', linestyle='--', 
                   label=f'平均价格: {predictions_df["Prediction"].mean():.0f}')
        ax2.set_title('预测价格分布')
        ax2.set_xlabel('价格')
        ax2.set_ylabel('频次')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 价格变化率
        ax3 = axes[1, 0]
        price_changes = predictions_df['Prediction'].pct_change() * 100
        ax3.plot(predictions_df['Date'][1:], price_changes[1:], 
                marker='o', color='green', linewidth=2)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax3.set_title('日价格变化率')
        ax3.set_xlabel('日期')
        ax3.set_ylabel('变化率 (%)')
        ax3.grid(True, alpha=0.3)
        
        # 4. 模型预测对比
        ax4 = axes[1, 1]
        model_cols = [col for col in predictions_df.columns if col.endswith('_Prediction')]
        for col in model_cols:
            model_name = col.replace('_Prediction', '')
            ax4.plot(predictions_df['Date'], predictions_df[col], 
                    label=model_name, alpha=0.7, linewidth=1)
        
        ax4.plot(predictions_df['Date'], predictions_df['Prediction'], 
                label='集成预测', color='red', linewidth=2)
        ax4.set_title('模型预测对比')
        ax4.set_xlabel('日期')
        ax4.set_ylabel('价格')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"FFA预测可视化图已保存到: {save_path}")
    
    def save_ffa_predictions(self, predictions_df, save_path='prediction/ffa_predictions.csv'):
        """保存FFA预测结果"""
        predictions_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"FFA预测结果已保存到: {save_path}")
    
    def generate_ffa_report(self, predictions_df, multi_horizon_preds, 
                          save_path='prediction/ffa_report.txt'):
        """生成FFA预测报告"""
        summary = self.get_prediction_summary(predictions_df)
        
        report = []
        report.append("=" * 80)
        report.append("FFA价格预测报告")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"预测产品: {summary['product']}")
        report.append("")
        
        # 预测摘要
        report.append("预测摘要:")
        report.append("-" * 40)
        report.append(f"当前价格: {summary['current_price']:,.2f}")
        report.append(f"未来价格: {summary['future_price']:,.2f}")
        report.append(f"价格变化: {summary['price_change']:,.2f}")
        report.append(f"变化率: {summary['change_rate']:.2f}%")
        report.append(f"趋势: {summary['trend']}")
        report.append(f"置信度: {summary['confidence']}")
        report.append(f"波动率: {summary['volatility']:.2f}%")
        report.append("")
        
        # 详细预测
        report.append("详细预测:")
        report.append("-" * 40)
        for _, row in predictions_df.iterrows():
            report.append(f"{row['Date'].strftime('%Y-%m-%d')}: {row['Prediction']:,.2f}")
        
        # 多时间跨度分析
        report.append("\n多时间跨度分析:")
        report.append("-" * 40)
        for horizon, pred_data in multi_horizon_preds.items():
            ensemble_pred = pred_data['ensemble']
            report.append(f"{horizon}: 平均价格 {ensemble_pred.mean():,.2f}, 标准差 {ensemble_pred.std():,.2f}")
        
        # 保存报告
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"FFA预测报告已保存到: {save_path}")
        
        # 打印到控制台
        print('\n'.join(report))
