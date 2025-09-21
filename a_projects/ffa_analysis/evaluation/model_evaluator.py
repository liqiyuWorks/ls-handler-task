#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型评估器 - 评估模型性能并生成可视化报告
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ModelEvaluator:
    """模型评估器"""
    
    def __init__(self):
        self.evaluation_results = {}
        self.prediction_results = {}
        
    def evaluate_models(self, models, X_test, y_test, model_names=None):
        """评估所有模型"""
        print("正在评估模型性能...")
        
        if model_names is None:
            model_names = list(models.keys())
        
        results = {}
        
        for name in model_names:
            if name not in models or models[name] is None:
                continue
            
            print(f"评估 {name}...")
            
            try:
                # 获取模型和预测
                model = models[name]
                y_pred = self._get_predictions(model, X_test, name)
                
                # 计算评估指标
                metrics = self._calculate_metrics(y_test, y_pred)
                
                # 交叉验证
                cv_scores = self._cross_validate(model, X_test, y_test, name)
                
                results[name] = {
                    'metrics': metrics,
                    'cv_scores': cv_scores,
                    'predictions': y_pred
                }
                
                print(f"  RMSE: {metrics['rmse']:.2f}, R²: {metrics['r2']:.3f}, CV: {cv_scores['mean']:.3f}±{cv_scores['std']:.3f}")
                
            except Exception as e:
                print(f"  {name} 评估失败: {e}")
                results[name] = None
        
        self.evaluation_results = results
        return results
    
    def _get_predictions(self, model, X_test, model_name):
        """获取模型预测"""
        if hasattr(model, 'predict'):
            return model.predict(X_test)
        elif hasattr(model, 'forecast'):
            return model.forecast(len(X_test))
        else:
            raise ValueError(f"模型 {model_name} 不支持预测")
    
    def _calculate_metrics(self, y_true, y_pred):
        """计算评估指标"""
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        # 方向准确率
        direction_accuracy = self._calculate_direction_accuracy(y_true, y_pred)
        
        return {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape,
            'direction_accuracy': direction_accuracy
        }
    
    def _calculate_direction_accuracy(self, y_true, y_pred):
        """计算方向准确率"""
        true_direction = np.diff(y_true) > 0
        pred_direction = np.diff(y_pred) > 0
        return np.mean(true_direction == pred_direction) * 100
    
    def _cross_validate(self, model, X, y, model_name, cv=5):
        """交叉验证"""
        try:
            if hasattr(model, 'predict'):
                scores = cross_val_score(model, X, y, cv=cv, scoring='r2')
                return {
                    'mean': scores.mean(),
                    'std': scores.std(),
                    'scores': scores
                }
            else:
                return {'mean': 0, 'std': 0, 'scores': []}
        except:
            return {'mean': 0, 'std': 0, 'scores': []}
    
    def create_performance_comparison(self, save_path='evaluation/performance_comparison.png'):
        """创建性能对比图"""
        print("正在创建性能对比图...")
        
        # 准备数据
        data = []
        for name, result in self.evaluation_results.items():
            if result is None:
                continue
            
            metrics = result['metrics']
            data.append({
                'Model': name,
                'RMSE': metrics['rmse'],
                'MAE': metrics['mae'],
                'R²': metrics['r2'],
                'MAPE': metrics['mape'],
                'Direction_Accuracy': metrics['direction_accuracy']
            })
        
        df = pd.DataFrame(data)
        
        # 创建图表
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('模型性能对比', fontsize=16, fontweight='bold')
        
        # RMSE对比
        ax1 = axes[0, 0]
        sns.barplot(data=df, x='Model', y='RMSE', ax=ax1)
        ax1.set_title('RMSE对比')
        ax1.tick_params(axis='x', rotation=45)
        
        # MAE对比
        ax2 = axes[0, 1]
        sns.barplot(data=df, x='Model', y='MAE', ax=ax2)
        ax2.set_title('MAE对比')
        ax2.tick_params(axis='x', rotation=45)
        
        # R²对比
        ax3 = axes[0, 2]
        sns.barplot(data=df, x='Model', y='R²', ax=ax3)
        ax3.set_title('R²对比')
        ax3.tick_params(axis='x', rotation=45)
        
        # MAPE对比
        ax4 = axes[1, 0]
        sns.barplot(data=df, x='Model', y='MAPE', ax=ax4)
        ax4.set_title('MAPE对比')
        ax4.tick_params(axis='x', rotation=45)
        
        # 方向准确率对比
        ax5 = axes[1, 1]
        sns.barplot(data=df, x='Model', y='Direction_Accuracy', ax=ax5)
        ax5.set_title('方向准确率对比')
        ax5.tick_params(axis='x', rotation=45)
        
        # 综合评分
        ax6 = axes[1, 2]
        df['综合评分'] = (df['R²'] * 0.4 + (1 - df['MAPE']/100) * 0.3 + df['Direction_Accuracy']/100 * 0.3)
        sns.barplot(data=df, x='Model', y='综合评分', ax=ax6)
        ax6.set_title('综合评分对比')
        ax6.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"性能对比图已保存到: {save_path}")
    
    def create_prediction_comparison(self, y_true, model_predictions, save_path='evaluation/prediction_comparison.png'):
        """创建预测对比图"""
        print("正在创建预测对比图...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('预测结果对比', fontsize=16, fontweight='bold')
        
        # 时间序列对比
        ax1 = axes[0, 0]
        ax1.plot(y_true, label='实际值', color='blue', linewidth=2)
        
        colors = ['red', 'green', 'orange', 'purple', 'brown']
        for i, (name, y_pred) in enumerate(model_predictions.items()):
            if y_pred is not None:
                ax1.plot(y_pred, label=f'{name}预测', color=colors[i % len(colors)], 
                        linestyle='--', alpha=0.8)
        
        ax1.set_title('时间序列对比')
        ax1.set_xlabel('时间')
        ax1.set_ylabel('价格')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 散点图对比
        ax2 = axes[0, 1]
        for i, (name, y_pred) in enumerate(model_predictions.items()):
            if y_pred is not None:
                ax2.scatter(y_true, y_pred, alpha=0.6, label=name, 
                           color=colors[i % len(colors)])
        
        # 完美预测线
        min_val = min(y_true.min(), min([y_pred.min() for y_pred in model_predictions.values() if y_pred is not None]))
        max_val = max(y_true.max(), max([y_pred.max() for y_pred in model_predictions.values() if y_pred is not None]))
        ax2.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='完美预测')
        
        ax2.set_title('预测值 vs 实际值')
        ax2.set_xlabel('实际值')
        ax2.set_ylabel('预测值')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 残差分析
        ax3 = axes[1, 0]
        for i, (name, y_pred) in enumerate(model_predictions.items()):
            if y_pred is not None:
                residuals = y_true - y_pred
                ax3.scatter(y_pred, residuals, alpha=0.6, label=name,
                           color=colors[i % len(colors)])
        
        ax3.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        ax3.set_title('残差分析')
        ax3.set_xlabel('预测值')
        ax3.set_ylabel('残差')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 误差分布
        ax4 = axes[1, 1]
        for i, (name, y_pred) in enumerate(model_predictions.items()):
            if y_pred is not None:
                errors = np.abs(y_true - y_pred)
                ax4.hist(errors, alpha=0.6, label=name, bins=20,
                        color=colors[i % len(colors)])
        
        ax4.set_title('绝对误差分布')
        ax4.set_xlabel('绝对误差')
        ax4.set_ylabel('频次')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"预测对比图已保存到: {save_path}")
    
    def create_feature_importance_plot(self, feature_importance_dict, save_path='evaluation/feature_importance.png'):
        """创建特征重要性图"""
        print("正在创建特征重要性图...")
        
        fig, axes = plt.subplots(1, len(feature_importance_dict), figsize=(6*len(feature_importance_dict), 6))
        if len(feature_importance_dict) == 1:
            axes = [axes]
        
        for i, (model_name, importance) in enumerate(feature_importance_dict.items()):
            if importance is None:
                continue
            
            # 获取前20个重要特征
            top_features = sorted(importance, key=lambda x: x[1], reverse=True)[:20]
            features, scores = zip(*top_features)
            
            ax = axes[i] if len(feature_importance_dict) > 1 else axes[0]
            ax.barh(range(len(features)), scores)
            ax.set_yticks(range(len(features)))
            ax.set_yticklabels(features)
            ax.set_title(f'{model_name} 特征重要性')
            ax.set_xlabel('重要性')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"特征重要性图已保存到: {save_path}")
    
    def generate_evaluation_report(self, save_path='evaluation/evaluation_report.txt'):
        """生成评估报告"""
        print("正在生成评估报告...")
        
        report = []
        report.append("=" * 60)
        report.append("FFA价格预测模型评估报告")
        report.append("=" * 60)
        report.append("")
        
        # 模型性能总结
        report.append("模型性能总结:")
        report.append("-" * 30)
        
        for name, result in self.evaluation_results.items():
            if result is None:
                continue
            
            metrics = result['metrics']
            report.append(f"\n{name}:")
            report.append(f"  RMSE: {metrics['rmse']:.2f}")
            report.append(f"  MAE: {metrics['mae']:.2f}")
            report.append(f"  R²: {metrics['r2']:.3f}")
            report.append(f"  MAPE: {metrics['mape']:.2f}%")
            report.append(f"  方向准确率: {metrics['direction_accuracy']:.2f}%")
            
            if 'cv_scores' in result:
                cv = result['cv_scores']
                report.append(f"  交叉验证: {cv['mean']:.3f}±{cv['std']:.3f}")
        
        # 最佳模型推荐
        report.append("\n最佳模型推荐:")
        report.append("-" * 30)
        
        best_models = {}
        for name, result in self.evaluation_results.items():
            if result is None:
                continue
            
            metrics = result['metrics']
            # 综合评分
            score = (metrics['r2'] * 0.4 + (1 - metrics['mape']/100) * 0.3 + 
                    metrics['direction_accuracy']/100 * 0.3)
            best_models[name] = score
        
        sorted_models = sorted(best_models.items(), key=lambda x: x[1], reverse=True)
        
        for i, (name, score) in enumerate(sorted_models[:5]):
            report.append(f"{i+1}. {name}: {score:.3f}")
        
        # 保存报告
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"评估报告已保存到: {save_path}")
        
        # 打印到控制台
        print('\n'.join(report))
