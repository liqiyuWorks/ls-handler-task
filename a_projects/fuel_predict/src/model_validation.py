#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测模型验证模块
模型性能评估、可视化分析和业务验证

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, learning_curve
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ModelValidator:
    """模型验证器"""
    
    def __init__(self, predictor_system):
        """
        初始化验证器
        
        Args:
            predictor_system: 多船型预测系统实例
        """
        self.predictor_system = predictor_system
        self.validation_results = {}
        
    def comprehensive_validation(self, X_test: pd.DataFrame, y_test: pd.Series,
                                X_train: pd.DataFrame = None, y_train: pd.Series = None) -> Dict:
        """
        综合模型验证
        
        Args:
            X_test: 测试特征
            y_test: 测试目标
            X_train: 训练特征 (可选)
            y_train: 训练目标 (可选)
            
        Returns:
            验证结果字典
        """
        print("开始综合模型验证...")
        
        results = {}
        
        # 1. 基础性能指标
        results['basic_metrics'] = self._calculate_basic_metrics(X_test, y_test)
        
        # 2. 分船型性能分析
        results['ship_type_analysis'] = self._analyze_ship_type_performance(X_test, y_test)
        
        # 3. 载重状态分析
        results['load_condition_analysis'] = self._analyze_load_condition_performance(X_test, y_test)
        
        # 4. 速度区间分析
        results['speed_range_analysis'] = self._analyze_speed_range_performance(X_test, y_test)
        
        # 5. 残差分析
        results['residual_analysis'] = self._analyze_residuals(X_test, y_test)
        
        # 6. 业务验证
        results['business_validation'] = self._business_validation(X_test, y_test)
        
        # 7. 交叉验证 (如果提供训练数据)
        if X_train is not None and y_train is not None:
            results['cross_validation'] = self._cross_validation_analysis(X_train, y_train)
        
        self.validation_results = results
        return results
    
    def _calculate_basic_metrics(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """计算基础性能指标"""
        print("计算基础性能指标...")
        
        y_pred = self.predictor_system.predict(X_test)
        
        metrics = {
            'MAE': mean_absolute_error(y_test, y_pred),
            'RMSE': np.sqrt(mean_squared_error(y_test, y_pred)),
            'R2': r2_score(y_test, y_pred),
            'MAPE': np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 0.01))) * 100,
            'Max_Error': np.max(np.abs(y_test - y_pred)),
            'Mean_Actual': np.mean(y_test),
            'Mean_Predicted': np.mean(y_pred),
            'Std_Actual': np.std(y_test),
            'Std_Predicted': np.std(y_pred)
        }
        
        return metrics
    
    def _analyze_ship_type_performance(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """分析各船型的预测性能"""
        print("分析各船型预测性能...")
        
        y_pred = self.predictor_system.predict(X_test)
        ship_analysis = {}
        
        for ship_type in X_test['船舶类型'].unique():
            ship_mask = X_test['船舶类型'] == ship_type
            y_test_ship = y_test[ship_mask]
            y_pred_ship = y_pred[ship_mask]
            
            if len(y_test_ship) > 0:
                ship_analysis[ship_type] = {
                    'sample_count': len(y_test_ship),
                    'MAE': mean_absolute_error(y_test_ship, y_pred_ship),
                    'RMSE': np.sqrt(mean_squared_error(y_test_ship, y_pred_ship)),
                    'R2': r2_score(y_test_ship, y_pred_ship),
                    'MAPE': np.mean(np.abs((y_test_ship - y_pred_ship) / np.maximum(y_test_ship, 0.01))) * 100,
                    'mean_actual': np.mean(y_test_ship),
                    'mean_predicted': np.mean(y_pred_ship),
                    'bias': np.mean(y_pred_ship - y_test_ship)
                }
        
        return ship_analysis
    
    def _analyze_load_condition_performance(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """分析载重状态的预测性能"""
        print("分析载重状态预测性能...")
        
        # 需要从原始数据中获取载重状态信息
        # 这里假设可以通过某种方式获取
        load_analysis = {}
        
        # 如果X_test中包含载重状态相关信息
        if 'load_factor' in X_test.columns:
            y_pred = self.predictor_system.predict(X_test)
            
            # 根据load_factor分组
            X_test_copy = X_test.copy()
            X_test_copy['load_condition'] = X_test_copy['load_factor'].apply(
                lambda x: 'Laden' if x > 0.8 else ('Ballast' if x < 0.2 else 'Part_Laden')
            )
            
            for condition in X_test_copy['load_condition'].unique():
                condition_mask = X_test_copy['load_condition'] == condition
                y_test_condition = y_test[condition_mask]
                y_pred_condition = y_pred[condition_mask]
                
                if len(y_test_condition) > 0:
                    load_analysis[condition] = {
                        'sample_count': len(y_test_condition),
                        'MAE': mean_absolute_error(y_test_condition, y_pred_condition),
                        'RMSE': np.sqrt(mean_squared_error(y_test_condition, y_pred_condition)),
                        'R2': r2_score(y_test_condition, y_pred_condition),
                        'MAPE': np.mean(np.abs((y_test_condition - y_pred_condition) / np.maximum(y_test_condition, 0.01))) * 100
                    }
        
        return load_analysis
    
    def _analyze_speed_range_performance(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """分析不同速度区间的预测性能"""
        print("分析速度区间预测性能...")
        
        y_pred = self.predictor_system.predict(X_test)
        speed_analysis = {}
        
        # 获取速度信息
        if '平均速度(kts)' in X_test.columns:
            speeds = X_test['平均速度(kts)']
            
            # 定义速度区间
            speed_bins = [0, 8, 12, 16, 20, 30]
            speed_labels = ['Very_Low', 'Low', 'Medium', 'High', 'Very_High']
            
            speed_categories = pd.cut(speeds, bins=speed_bins, labels=speed_labels, include_lowest=True)
            
            for category in speed_categories.unique():
                if pd.notna(category):
                    category_mask = speed_categories == category
                    y_test_category = y_test[category_mask]
                    y_pred_category = y_pred[category_mask]
                    
                    if len(y_test_category) > 0:
                        speed_analysis[str(category)] = {
                            'sample_count': len(y_test_category),
                            'MAE': mean_absolute_error(y_test_category, y_pred_category),
                            'RMSE': np.sqrt(mean_squared_error(y_test_category, y_pred_category)),
                            'R2': r2_score(y_test_category, y_pred_category),
                            'MAPE': np.mean(np.abs((y_test_category - y_pred_category) / np.maximum(y_test_category, 0.01))) * 100,
                            'speed_range': f"{speed_bins[speed_labels.index(str(category))]}-{speed_bins[speed_labels.index(str(category))+1]} kts"
                        }
        
        return speed_analysis
    
    def _analyze_residuals(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """残差分析"""
        print("进行残差分析...")
        
        y_pred = self.predictor_system.predict(X_test)
        residuals = y_test - y_pred
        
        residual_analysis = {
            'mean_residual': np.mean(residuals),
            'std_residual': np.std(residuals),
            'skewness': self._calculate_skewness(residuals),
            'kurtosis': self._calculate_kurtosis(residuals),
            'normality_test': self._test_normality(residuals),
            'outliers_count': np.sum(np.abs(residuals) > 3 * np.std(residuals)),
            'outliers_percentage': np.sum(np.abs(residuals) > 3 * np.std(residuals)) / len(residuals) * 100
        }
        
        return residual_analysis
    
    def _business_validation(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """业务验证"""
        print("进行业务验证...")
        
        y_pred = self.predictor_system.predict(X_test)
        
        # 业务规则验证
        business_validation = {
            'reasonable_predictions': {
                'positive_predictions': np.sum(y_pred > 0) / len(y_pred) * 100,
                'within_normal_range': np.sum((y_pred > 0.5) & (y_pred < 100)) / len(y_pred) * 100,
                'extreme_predictions': np.sum(y_pred > 100) / len(y_pred) * 100
            },
            'prediction_consistency': {
                'correlation_with_speed': self._calculate_correlation_with_speed(X_test, y_pred),
                'correlation_with_size': self._calculate_correlation_with_size(X_test, y_pred)
            },
            'industry_benchmarks': self._compare_with_industry_benchmarks(X_test, y_pred)
        }
        
        return business_validation
    
    def _cross_validation_analysis(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict:
        """交叉验证分析"""
        print("进行交叉验证分析...")
        
        cv_results = {}
        
        # 对每个船型进行交叉验证
        for ship_type, predictor in self.predictor_system.ship_predictors.items():
            if predictor.best_model is not None:
                # 获取该船型的训练数据
                ship_mask = X_train['船舶类型'] == ship_type
                X_ship = X_train[ship_mask].drop('船舶类型', axis=1)
                y_ship = y_train[ship_mask]
                
                if len(X_ship) > 10:  # 确保有足够数据进行交叉验证
                    try:
                        cv_scores = cross_val_score(
                            predictor.best_model, X_ship, y_ship,
                            cv=min(5, len(X_ship)//2), scoring='neg_mean_squared_error'
                        )
                        
                        cv_results[ship_type] = {
                            'cv_rmse_mean': np.sqrt(-cv_scores.mean()),
                            'cv_rmse_std': np.sqrt(cv_scores.std()),
                            'cv_scores': cv_scores.tolist()
                        }
                    except Exception as e:
                        print(f"交叉验证失败 {ship_type}: {e}")
        
        return cv_results
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """计算偏度"""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 3)
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """计算峰度"""
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0
        return np.mean(((data - mean) / std) ** 4) - 3
    
    def _test_normality(self, data: np.ndarray) -> Dict:
        """正态性检验"""
        try:
            from scipy import stats
            statistic, p_value = stats.jarque_bera(data)
            return {
                'test': 'Jarque-Bera',
                'statistic': statistic,
                'p_value': p_value,
                'is_normal': p_value > 0.05
            }
        except ImportError:
            return {'test': 'Not available', 'is_normal': 'Unknown'}
    
    def _calculate_correlation_with_speed(self, X_test: pd.DataFrame, y_pred: np.ndarray) -> float:
        """计算预测值与速度的相关性"""
        if '平均速度(kts)' in X_test.columns:
            return np.corrcoef(X_test['平均速度(kts)'], y_pred)[0, 1]
        return 0.0
    
    def _calculate_correlation_with_size(self, X_test: pd.DataFrame, y_pred: np.ndarray) -> float:
        """计算预测值与船舶大小的相关性"""
        if '船舶载重(t)' in X_test.columns:
            return np.corrcoef(X_test['船舶载重(t)'], y_pred)[0, 1]
        return 0.0
    
    def _compare_with_industry_benchmarks(self, X_test: pd.DataFrame, y_pred: np.ndarray) -> Dict:
        """与行业基准对比"""
        benchmarks = {}
        
        # 按船型计算平均油耗并与行业标准对比
        for ship_type in X_test['船舶类型'].unique():
            ship_mask = X_test['船舶类型'] == ship_type
            ship_pred = y_pred[ship_mask]
            
            if len(ship_pred) > 0:
                avg_consumption = np.mean(ship_pred)
                
                # 简单的行业基准 (这些值应该基于实际行业数据)
                industry_benchmarks = {
                    'BULK CARRIER': 25.0,
                    'CONTAINER SHIP': 180.0,
                    'TANKER': 35.0,
                    'General Cargo Ship': 15.0
                }
                
                if ship_type in industry_benchmarks:
                    benchmark = industry_benchmarks[ship_type]
                    deviation = (avg_consumption - benchmark) / benchmark * 100
                    
                    benchmarks[ship_type] = {
                        'predicted_avg': avg_consumption,
                        'industry_benchmark': benchmark,
                        'deviation_percent': deviation
                    }
        
        return benchmarks
    
    def create_validation_visualizations(self, X_test: pd.DataFrame, y_test: pd.Series, 
                                       save_path: str = None):
        """创建验证可视化图表"""
        print("创建验证可视化图表...")
        
        y_pred = self.predictor_system.predict(X_test)
        residuals = y_test - y_pred
        
        # 创建图表
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('模型验证分析仪表板', fontsize=16, fontweight='bold')
        
        # 1. 预测值 vs 实际值散点图
        axes[0,0].scatter(y_test, y_pred, alpha=0.6)
        axes[0,0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
        axes[0,0].set_xlabel('实际值 (mt/h)')
        axes[0,0].set_ylabel('预测值 (mt/h)')
        axes[0,0].set_title('预测值 vs 实际值')
        
        # 添加R²信息
        r2 = r2_score(y_test, y_pred)
        axes[0,0].text(0.05, 0.95, f'R² = {r2:.3f}', transform=axes[0,0].transAxes,
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # 2. 残差分布直方图
        axes[0,1].hist(residuals, bins=30, alpha=0.7, color='skyblue')
        axes[0,1].axvline(x=0, color='red', linestyle='--')
        axes[0,1].set_xlabel('残差 (mt/h)')
        axes[0,1].set_ylabel('频次')
        axes[0,1].set_title('残差分布')
        
        # 3. 残差 vs 预测值散点图
        axes[0,2].scatter(y_pred, residuals, alpha=0.6)
        axes[0,2].axhline(y=0, color='red', linestyle='--')
        axes[0,2].set_xlabel('预测值 (mt/h)')
        axes[0,2].set_ylabel('残差 (mt/h)')
        axes[0,2].set_title('残差 vs 预测值')
        
        # 4. 按船型的性能对比
        ship_types = X_test['船舶类型'].unique()[:5]  # 显示前5种船型
        ship_maes = []
        ship_names = []
        
        for ship_type in ship_types:
            ship_mask = X_test['船舶类型'] == ship_type
            if np.sum(ship_mask) > 0:
                ship_mae = mean_absolute_error(y_test[ship_mask], y_pred[ship_mask])
                ship_maes.append(ship_mae)
                ship_names.append(ship_type[:15])  # 截断长名称
        
        if ship_maes:
            axes[1,0].bar(range(len(ship_maes)), ship_maes)
            axes[1,0].set_xticks(range(len(ship_names)))
            axes[1,0].set_xticklabels(ship_names, rotation=45, ha='right')
            axes[1,0].set_ylabel('MAE (mt/h)')
            axes[1,0].set_title('各船型MAE对比')
        
        # 5. 速度 vs 油耗关系
        if '平均速度(kts)' in X_test.columns:
            speeds = X_test['平均速度(kts)']
            axes[1,1].scatter(speeds, y_test, alpha=0.6, label='实际值', color='blue')
            axes[1,1].scatter(speeds, y_pred, alpha=0.6, label='预测值', color='red')
            axes[1,1].set_xlabel('平均速度 (kts)')
            axes[1,1].set_ylabel('油耗 (mt/h)')
            axes[1,1].set_title('速度 vs 油耗关系')
            axes[1,1].legend()
        
        # 6. 误差分布箱线图
        error_percentages = np.abs((y_test - y_pred) / np.maximum(y_test, 0.01)) * 100
        axes[1,2].boxplot(error_percentages)
        axes[1,2].set_ylabel('绝对百分比误差 (%)')
        axes[1,2].set_title('误差分布')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"验证图表已保存至: {save_path}")
        
        return fig
    
    def generate_validation_report(self) -> str:
        """生成验证报告"""
        if not self.validation_results:
            return "尚未进行模型验证"
        
        report = "# 船舶油耗预测模型验证报告\n\n"
        
        # 基础性能指标
        if 'basic_metrics' in self.validation_results:
            metrics = self.validation_results['basic_metrics']
            report += "## 整体性能指标\n"
            report += f"- 平均绝对误差 (MAE): {metrics['MAE']:.3f} mt/h\n"
            report += f"- 均方根误差 (RMSE): {metrics['RMSE']:.3f} mt/h\n"
            report += f"- 决定系数 (R²): {metrics['R2']:.3f}\n"
            report += f"- 平均绝对百分比误差 (MAPE): {metrics['MAPE']:.1f}%\n"
            report += f"- 最大误差: {metrics['Max_Error']:.3f} mt/h\n\n"
        
        # 各船型性能分析
        if 'ship_type_analysis' in self.validation_results:
            report += "## 各船型性能分析\n"
            ship_analysis = self.validation_results['ship_type_analysis']
            
            for ship_type, metrics in ship_analysis.items():
                report += f"\n### {ship_type}\n"
                report += f"- 样本数量: {metrics['sample_count']}\n"
                report += f"- MAE: {metrics['MAE']:.3f} mt/h\n"
                report += f"- RMSE: {metrics['RMSE']:.3f} mt/h\n"
                report += f"- R²: {metrics['R2']:.3f}\n"
                report += f"- MAPE: {metrics['MAPE']:.1f}%\n"
                report += f"- 预测偏差: {metrics['bias']:.3f} mt/h\n"
        
        # 残差分析
        if 'residual_analysis' in self.validation_results:
            residual = self.validation_results['residual_analysis']
            report += "\n## 残差分析\n"
            report += f"- 残差均值: {residual['mean_residual']:.3f}\n"
            report += f"- 残差标准差: {residual['std_residual']:.3f}\n"
            report += f"- 偏度: {residual['skewness']:.3f}\n"
            report += f"- 峰度: {residual['kurtosis']:.3f}\n"
            report += f"- 异常值数量: {residual['outliers_count']}\n"
            report += f"- 异常值比例: {residual['outliers_percentage']:.1f}%\n"
        
        # 业务验证
        if 'business_validation' in self.validation_results:
            business = self.validation_results['business_validation']
            report += "\n## 业务验证\n"
            
            if 'reasonable_predictions' in business:
                reasonable = business['reasonable_predictions']
                report += "### 预测合理性\n"
                report += f"- 正值预测比例: {reasonable['positive_predictions']:.1f}%\n"
                report += f"- 正常范围预测比例: {reasonable['within_normal_range']:.1f}%\n"
                report += f"- 极端预测比例: {reasonable['extreme_predictions']:.1f}%\n"
            
            if 'industry_benchmarks' in business:
                benchmarks = business['industry_benchmarks']
                report += "\n### 行业基准对比\n"
                for ship_type, benchmark_data in benchmarks.items():
                    report += f"- {ship_type}:\n"
                    report += f"  - 预测平均值: {benchmark_data['predicted_avg']:.1f} mt/h\n"
                    report += f"  - 行业基准: {benchmark_data['industry_benchmark']:.1f} mt/h\n"
                    report += f"  - 偏差: {benchmark_data['deviation_percent']:.1f}%\n"
        
        report += "\n## 结论和建议\n"
        report += self._generate_conclusions()
        
        return report
    
    def _generate_conclusions(self) -> str:
        """生成结论和建议"""
        conclusions = ""
        
        if 'basic_metrics' in self.validation_results:
            metrics = self.validation_results['basic_metrics']
            r2 = metrics['R2']
            mape = metrics['MAPE']
            
            if r2 > 0.8:
                conclusions += "- 模型整体性能优秀，R²超过0.8，具有很强的预测能力\n"
            elif r2 > 0.6:
                conclusions += "- 模型整体性能良好，R²超过0.6，具有较好的预测能力\n"
            else:
                conclusions += "- 模型整体性能需要改进，建议优化特征工程或模型结构\n"
            
            if mape < 10:
                conclusions += "- 预测精度很高，MAPE小于10%，可用于实际业务\n"
            elif mape < 20:
                conclusions += "- 预测精度较好，MAPE小于20%，适合大多数应用场景\n"
            else:
                conclusions += "- 预测精度有待提高，建议进一步优化模型\n"
        
        conclusions += "- 建议定期重新训练模型以保持预测准确性\n"
        conclusions += "- 建议收集更多高质量数据以改善模型性能\n"
        conclusions += "- 建议结合领域专家知识进一步优化特征工程\n"
        
        return conclusions

def main():
    """主函数示例"""
    # 这里需要先训练好模型系统
    print("模型验证模块已准备就绪")
    print("使用方法:")
    print("1. 首先训练好预测系统")
    print("2. 创建验证器: validator = ModelValidator(predictor_system)")
    print("3. 执行验证: results = validator.comprehensive_validation(X_test, y_test)")
    print("4. 生成报告: report = validator.generate_validation_report()")
    print("5. 创建可视化: validator.create_validation_visualizations(X_test, y_test)")

if __name__ == "__main__":
    main()
