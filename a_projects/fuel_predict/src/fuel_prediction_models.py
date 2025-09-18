#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测模型模块
基于不同船型的专业化预测模型

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pandas as pd
import numpy as np
import pickle
import json
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

from .feature_engineering import ShipFuelFeatureEngineer
from .cp_clause_definitions import ShipType, LoadCondition

class ShipTypePredictor:
    """单个船型的油耗预测器"""
    
    def __init__(self, ship_type: str):
        """
        初始化船型预测器
        
        Args:
            ship_type: 船舶类型
        """
        self.ship_type = ship_type
        self.models = {}
        self.best_model_name = None
        self.best_model = None
        self.feature_importance = {}
        self.performance_metrics = {}
        
    def train_models(self, X_train: pd.DataFrame, y_train: pd.Series, 
                    X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
        """
        训练多个模型并选择最佳模型
        
        Args:
            X_train: 训练特征
            y_train: 训练目标
            X_val: 验证特征
            y_val: 验证目标
            
        Returns:
            各模型性能字典
        """
        print(f"训练 {self.ship_type} 船型预测模型...")
        
        # 定义模型
        models = {
            'Random Forest': RandomForestRegressor(
                n_estimators=100, max_depth=15, min_samples_split=5,
                min_samples_leaf=2, random_state=42, n_jobs=-1
            ),
            'XGBoost': xgb.XGBRegressor(
                n_estimators=100, max_depth=8, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8, random_state=42,
                objective='reg:squarederror'
            ),
            'LightGBM': lgb.LGBMRegressor(
                n_estimators=100, max_depth=8, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8, random_state=42,
                verbose=-1
            ),
            'Gradient Boosting': GradientBoostingRegressor(
                n_estimators=100, max_depth=8, learning_rate=0.1,
                subsample=0.8, random_state=42
            ),
            'Ridge Regression': Ridge(alpha=1.0),
            'Neural Network': MLPRegressor(
                hidden_layer_sizes=(100, 50), max_iter=500,
                random_state=42, early_stopping=True
            )
        }
        
        performance = {}
        
        for name, model in models.items():
            try:
                # 训练模型
                model.fit(X_train, y_train)
                
                # 预测
                y_pred = model.predict(X_val)
                
                # 计算指标
                mae = mean_absolute_error(y_val, y_pred)
                rmse = np.sqrt(mean_squared_error(y_val, y_pred))
                r2 = r2_score(y_val, y_pred)
                
                # 计算平均绝对百分比误差
                mape = np.mean(np.abs((y_val - y_pred) / np.maximum(y_val, 0.01))) * 100
                
                performance[name] = {
                    'MAE': mae,
                    'RMSE': rmse,
                    'R2': r2,
                    'MAPE': mape
                }
                
                self.models[name] = model
                
                print(f"{name}: MAE={mae:.3f}, RMSE={rmse:.3f}, R2={r2:.3f}, MAPE={mape:.1f}%")
                
            except Exception as e:
                print(f"{name} 训练失败: {e}")
                continue
        
        # 选择最佳模型 (基于RMSE)
        if performance:
            best_model_name = min(performance.keys(), key=lambda x: performance[x]['RMSE'])
            self.best_model_name = best_model_name
            self.best_model = self.models[best_model_name]
            self.performance_metrics = performance
            
            print(f"最佳模型: {best_model_name}")
            
            # 计算特征重要性
            self._calculate_feature_importance(X_train)
        
        return performance
    
    def _calculate_feature_importance(self, X_train: pd.DataFrame):
        """计算特征重要性"""
        if self.best_model is None:
            return
        
        try:
            if hasattr(self.best_model, 'feature_importances_'):
                # 树模型的特征重要性
                importance = self.best_model.feature_importances_
            elif hasattr(self.best_model, 'coef_'):
                # 线性模型的系数绝对值
                importance = np.abs(self.best_model.coef_)
            else:
                return
            
            # 创建特征重要性字典
            feature_names = X_train.columns.tolist()
            self.feature_importance = dict(zip(feature_names, importance))
            
            # 排序
            self.feature_importance = dict(
                sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)
            )
            
        except Exception as e:
            print(f"特征重要性计算失败: {e}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """预测油耗"""
        if self.best_model is None:
            raise ValueError("模型尚未训练")
        
        return self.best_model.predict(X)
    
    def get_top_features(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """获取最重要的特征"""
        if not self.feature_importance:
            return []
        
        return list(self.feature_importance.items())[:top_k]

class MultiShipTypePredictor:
    """多船型油耗预测系统"""
    
    def __init__(self):
        """初始化多船型预测系统"""
        self.ship_predictors = {}
        self.feature_engineer = ShipFuelFeatureEngineer()
        self.global_model = None  # 全局模型作为备选
        self.ship_type_mapping = {}
        
    def prepare_data(self, df: pd.DataFrame, target_col: str = '小时油耗(mt/h)') -> Tuple[pd.DataFrame, pd.Series]:
        """准备训练数据"""
        print("准备训练数据...")
        
        # 过滤有效数据
        valid_data = df[
            (df['航行距离(nm)'] > 0) & 
            (df[target_col] > 0) &
            (df[target_col] < df[target_col].quantile(0.99)) &  # 移除异常值
            (df['平均速度(kts)'] > 0) &
            (df['平均速度(kts)'] < 25) &  # 移除异常速度
            (df['航行时间(hrs)'] > 0)
        ].copy()
        
        print(f"有效数据: {len(valid_data)} 条")
        
        # 特征工程
        df_engineered = self.feature_engineer.engineer_features(valid_data, target_col=target_col, fit=True)
        
        # 准备特征和目标
        feature_cols = [col for col in df_engineered.columns if 
                       col not in ['报告时间', target_col, 'MMSI', 'IMO', '航次ID', '船舶类型'] and
                       df_engineered[col].dtype in ['int64', 'float64']]
        
        X = df_engineered[feature_cols].fillna(0)
        y = df_engineered[target_col]
        
        # 保存船型信息
        ship_types = df_engineered['船舶类型']
        X['船舶类型'] = ship_types
        
        print(f"特征数量: {len(feature_cols)}")
        print(f"目标变量范围: {y.min():.3f} - {y.max():.3f}")
        
        return X, y
    
    def train_ship_type_models(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> Dict[str, Dict]:
        """为每个船型训练专门的模型"""
        print("开始训练分船型模型...")
        
        ship_performance = {}
        
        # 获取船型分布
        ship_type_counts = X['船舶类型'].value_counts()
        print(f"\n船型分布:")
        for ship_type, count in ship_type_counts.items():
            print(f"  {ship_type}: {count} 条数据")
        
        for ship_type in ship_type_counts.index:
            if ship_type_counts[ship_type] < 50:  # 数据量太少的船型跳过
                print(f"\n跳过 {ship_type} (数据量不足: {ship_type_counts[ship_type]})")
                continue
            
            print(f"\n{'='*50}")
            print(f"训练 {ship_type} 模型")
            print(f"{'='*50}")
            
            # 提取该船型的数据
            ship_mask = X['船舶类型'] == ship_type
            X_ship = X[ship_mask].drop('船舶类型', axis=1)
            y_ship = y[ship_mask]
            
            # 分割训练和验证集
            X_train, X_val, y_train, y_val = train_test_split(
                X_ship, y_ship, test_size=test_size, random_state=42
            )
            
            # 创建船型预测器
            predictor = ShipTypePredictor(ship_type)
            
            # 训练模型
            performance = predictor.train_models(X_train, y_train, X_val, y_val)
            
            if performance:
                self.ship_predictors[ship_type] = predictor
                ship_performance[ship_type] = performance
                
                # 显示最重要的特征
                top_features = predictor.get_top_features(5)
                if top_features:
                    print(f"\n{ship_type} 最重要特征:")
                    for i, (feature, importance) in enumerate(top_features, 1):
                        print(f"  {i}. {feature}: {importance:.4f}")
        
        return ship_performance
    
    def train_global_model(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """训练全局模型作为备选"""
        print(f"\n{'='*50}")
        print("训练全局模型")
        print(f"{'='*50}")
        
        # 移除船型列
        X_global = X.drop('船舶类型', axis=1)
        
        # 分割数据
        X_train, X_val, y_train, y_val = train_test_split(
            X_global, y, test_size=0.2, random_state=42
        )
        
        # 训练全局模型
        global_predictor = ShipTypePredictor("Global")
        performance = global_predictor.train_models(X_train, y_train, X_val, y_val)
        
        if performance:
            self.global_model = global_predictor
            
            # 显示全局模型最重要特征
            top_features = global_predictor.get_top_features(10)
            if top_features:
                print(f"\n全局模型最重要特征:")
                for i, (feature, importance) in enumerate(top_features, 1):
                    print(f"  {i:2d}. {feature}: {importance:.4f}")
        
        return performance
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """预测油耗"""
        if '船舶类型' not in X.columns:
            raise ValueError("输入数据必须包含船舶类型")
        
        predictions = np.zeros(len(X))
        
        for i, ship_type in enumerate(X['船舶类型']):
            # 准备单条数据
            X_single = X.iloc[i:i+1].drop('船舶类型', axis=1)
            
            # 选择对应的模型
            if ship_type in self.ship_predictors:
                pred = self.ship_predictors[ship_type].predict(X_single)[0]
            elif self.global_model is not None:
                pred = self.global_model.predict(X_single)[0]
            else:
                pred = 0.0  # 默认值
            
            predictions[i] = max(pred, 0)  # 确保预测值非负
        
        return predictions
    
    def evaluate_models(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Dict[str, float]]:
        """评估模型性能"""
        print(f"\n{'='*50}")
        print("模型性能评估")
        print(f"{'='*50}")
        
        evaluation_results = {}
        
        # 整体预测
        y_pred = self.predict(X_test)
        
        # 整体指标
        overall_metrics = {
            'MAE': mean_absolute_error(y_test, y_pred),
            'RMSE': np.sqrt(mean_squared_error(y_test, y_pred)),
            'R2': r2_score(y_test, y_pred),
            'MAPE': np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 0.01))) * 100
        }
        
        evaluation_results['Overall'] = overall_metrics
        
        print(f"整体性能:")
        print(f"  MAE: {overall_metrics['MAE']:.3f}")
        print(f"  RMSE: {overall_metrics['RMSE']:.3f}")
        print(f"  R²: {overall_metrics['R2']:.3f}")
        print(f"  MAPE: {overall_metrics['MAPE']:.1f}%")
        
        # 分船型评估
        for ship_type in X_test['船舶类型'].unique():
            if ship_type in self.ship_predictors:
                ship_mask = X_test['船舶类型'] == ship_type
                y_test_ship = y_test[ship_mask]
                y_pred_ship = y_pred[ship_mask]
                
                if len(y_test_ship) > 0:
                    ship_metrics = {
                        'MAE': mean_absolute_error(y_test_ship, y_pred_ship),
                        'RMSE': np.sqrt(mean_squared_error(y_test_ship, y_pred_ship)),
                        'R2': r2_score(y_test_ship, y_pred_ship),
                        'MAPE': np.mean(np.abs((y_test_ship - y_pred_ship) / np.maximum(y_test_ship, 0.01))) * 100,
                        'Sample_Count': len(y_test_ship)
                    }
                    
                    evaluation_results[ship_type] = ship_metrics
                    
                    print(f"\n{ship_type} ({len(y_test_ship)} 样本):")
                    print(f"  MAE: {ship_metrics['MAE']:.3f}")
                    print(f"  RMSE: {ship_metrics['RMSE']:.3f}")
                    print(f"  R²: {ship_metrics['R2']:.3f}")
                    print(f"  MAPE: {ship_metrics['MAPE']:.1f}%")
        
        return evaluation_results
    
    def save_models(self, save_path: str):
        """保存模型"""
        model_data = {
            'ship_predictors': {},
            'global_model': self.global_model,
            'feature_engineer': self.feature_engineer
        }
        
        # 保存各船型模型
        for ship_type, predictor in self.ship_predictors.items():
            model_data['ship_predictors'][ship_type] = {
                'best_model': predictor.best_model,
                'best_model_name': predictor.best_model_name,
                'feature_importance': predictor.feature_importance,
                'performance_metrics': predictor.performance_metrics
            }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"模型已保存至: {save_path}")
    
    def load_models(self, load_path: str):
        """加载模型"""
        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)
        
        # 恢复船型预测器
        self.ship_predictors = {}
        for ship_type, predictor_data in model_data['ship_predictors'].items():
            predictor = ShipTypePredictor(ship_type)
            predictor.best_model = predictor_data['best_model']
            predictor.best_model_name = predictor_data['best_model_name']
            predictor.feature_importance = predictor_data['feature_importance']
            predictor.performance_metrics = predictor_data['performance_metrics']
            self.ship_predictors[ship_type] = predictor
        
        # 恢复全局模型和特征工程器
        self.global_model = model_data['global_model']
        self.feature_engineer = model_data['feature_engineer']
        
        print(f"模型已从 {load_path} 加载")
    
    def generate_model_report(self) -> str:
        """生成模型报告"""
        report = "# 船舶油耗预测模型报告\n\n"
        
        report += "## 模型概述\n"
        report += f"- 训练的船型数量: {len(self.ship_predictors)}\n"
        report += f"- 全局模型: {'是' if self.global_model else '否'}\n\n"
        
        report += "## 各船型模型性能\n"
        for ship_type, predictor in self.ship_predictors.items():
            report += f"\n### {ship_type}\n"
            report += f"- 最佳模型: {predictor.best_model_name}\n"
            
            if predictor.performance_metrics and predictor.best_model_name in predictor.performance_metrics:
                metrics = predictor.performance_metrics[predictor.best_model_name]
                report += f"- MAE: {metrics['MAE']:.3f}\n"
                report += f"- RMSE: {metrics['RMSE']:.3f}\n"
                report += f"- R²: {metrics['R2']:.3f}\n"
                report += f"- MAPE: {metrics['MAPE']:.1f}%\n"
            
            # 重要特征
            top_features = predictor.get_top_features(5)
            if top_features:
                report += f"- 重要特征:\n"
                for i, (feature, importance) in enumerate(top_features, 1):
                    report += f"  {i}. {feature}: {importance:.4f}\n"
        
        return report

def main():
    """主函数示例"""
    # 加载数据
    df = pd.read_csv('/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/油耗数据ALL（0804）.csv')
    
    # 初始化多船型预测系统
    predictor_system = MultiShipTypePredictor()
    
    # 准备数据
    X, y = predictor_system.prepare_data(df, target_col='小时油耗(mt/h)')
    
    # 分割训练测试集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"训练集: {len(X_train)} 条")
    print(f"测试集: {len(X_test)} 条")
    
    # 训练分船型模型
    ship_performance = predictor_system.train_ship_type_models(X_train, y_train)
    
    # 训练全局模型
    global_performance = predictor_system.train_global_model(X_train, y_train)
    
    # 评估模型
    evaluation_results = predictor_system.evaluate_models(X_test, y_test)
    
    # 保存模型
    model_save_path = '/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/fuel_prediction_models.pkl'
    predictor_system.save_models(model_save_path)
    
    # 生成报告
    report = predictor_system.generate_model_report()
    report_path = '/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/model_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n模型报告已保存至: {report_path}")
    
    # 保存评估结果
    results_path = '/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/evaluation_results.json'
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(evaluation_results, f, indent=2, ensure_ascii=False)
    
    print(f"评估结果已保存至: {results_path}")
    print("\n模型训练完成！")

if __name__ == "__main__":
    main()
