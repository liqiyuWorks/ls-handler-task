#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模型工厂 - 专门为FFA市场设计的模型工厂
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet, LinearRegression
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score, GridSearchCV, TimeSeriesSplit
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
warnings.filterwarnings('ignore')

from config.model_config import MODEL_CONFIG, FFA_CONFIG

class FFAModelFactory:
    """FFA模型工厂"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.best_models = {}
        self.model_scores = {}
        self.config = MODEL_CONFIG
        
    def create_ffa_models(self, horizon_type='short_term'):
        """创建FFA模型"""
        print(f"正在创建{horizon_type}FFA模型...")
        
        models = {}
        
        # 线性模型
        for model_name in self.config['ensemble_models']['linear_models']:
            if model_name == 'LinearRegression':
                models[model_name] = LinearRegression()
            elif model_name == 'Ridge':
                models[model_name] = Ridge(alpha=1.0)
            elif model_name == 'Lasso':
                models[model_name] = Lasso(alpha=0.1)
            elif model_name == 'ElasticNet':
                models[model_name] = ElasticNet(alpha=0.1, l1_ratio=0.5)
        
        # 树模型
        for model_name in self.config['ensemble_models']['tree_models']:
            if model_name == 'RandomForest':
                models[model_name] = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            elif model_name == 'ExtraTrees':
                models[model_name] = ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            elif model_name == 'GradientBoosting':
                models[model_name] = GradientBoostingRegressor(n_estimators=100, random_state=42)
        
        # 神经网络模型
        for model_name in self.config['ensemble_models']['neural_models']:
            if model_name == 'MLPRegressor':
                models[model_name] = MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42)
            elif model_name == 'SVR':
                models[model_name] = SVR(kernel='rbf', C=1.0, gamma='scale')
        
        # 时间序列模型
        for model_name in self.config['ensemble_models']['time_series_models']:
            if model_name in ['ARIMA', 'SARIMAX']:
                models[model_name] = None  # 特殊处理
        
        return models
    
    def train_ffa_models(self, X_train, X_val, y_train, y_val, horizon_type='short_term', model_names=None):
        """训练FFA模型"""
        print(f"正在训练{horizon_type}FFA模型...")
        
        if model_names is None:
            model_names = list(self.create_ffa_models(horizon_type).keys())
        
        models = self.create_ffa_models(horizon_type)
        results = {}
        
        for name in model_names:
            if name not in models or models[name] is None:
                continue
            
            print(f"训练 {name}...")
            
            try:
                if name in ['ARIMA', 'SARIMAX']:
                    # 时间序列模型特殊处理
                    score = self._train_time_series_model(name, y_train, y_val)
                else:
                    # 传统机器学习模型
                    score = self._train_ml_model(name, models[name], X_train, X_val, y_train, y_val, horizon_type)
                
                results[name] = score
                print(f"  {name} - RMSE: {score['rmse']:.2f}, R²: {score['r2']:.3f}")
                
            except Exception as e:
                print(f"  {name} 训练失败: {e}")
                results[name] = None
        
        self.model_scores = results
        return results
    
    def _train_ml_model(self, name, model, X_train, X_val, y_train, y_val, horizon_type):
        """训练机器学习模型"""
        # 数据标准化
        if name in ['Ridge', 'Lasso', 'ElasticNet', 'SVR', 'MLPRegressor']:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            self.scalers[name] = scaler
        else:
            X_train_scaled = X_train
            X_val_scaled = X_val
        
        # 训练模型
        model.fit(X_train_scaled, y_train)
        self.models[name] = model
        
        # 预测和评估
        y_pred = model.predict(X_val_scaled)
        
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        mape = np.mean(np.abs((y_val - y_pred) / y_val)) * 100
        
        # 方向准确率
        direction_accuracy = self._calculate_direction_accuracy(y_val, y_pred)
        
        return {
            'model': model,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape,
            'direction_accuracy': direction_accuracy
        }
    
    def _train_time_series_model(self, name, y_train, y_val):
        """训练时间序列模型"""
        try:
            if name == 'ARIMA':
                model = ARIMA(y_train, order=(1, 1, 1))
                fitted_model = model.fit()
            elif name == 'SARIMAX':
                model = SARIMAX(y_train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
                fitted_model = model.fit(disp=False)
            
            self.models[name] = fitted_model
            
            # 预测
            y_pred = fitted_model.forecast(len(y_val))
            
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))
            mae = mean_absolute_error(y_val, y_pred)
            r2 = r2_score(y_val, y_pred)
            mape = np.mean(np.abs((y_val - y_pred) / y_val)) * 100
            direction_accuracy = self._calculate_direction_accuracy(y_val, y_pred)
            
            return {
                'model': fitted_model,
                'rmse': rmse,
                'mae': mae,
                'r2': r2,
                'mape': mape,
                'direction_accuracy': direction_accuracy
            }
        except Exception as e:
            raise Exception(f"时间序列模型训练失败: {e}")
    
    def _calculate_direction_accuracy(self, y_true, y_pred):
        """计算方向准确率"""
        true_direction = np.diff(y_true) > 0
        pred_direction = np.diff(y_pred) > 0
        return np.mean(true_direction == pred_direction) * 100
    
    def select_best_ffa_models(self, criteria='rmse', horizon_type='short_term'):
        """选择最佳FFA模型"""
        print(f"基于 {criteria} 选择最佳{horizon_type}模型...")
        
        best_models = {}
        
        for name, score in self.model_scores.items():
            if score is None:
                continue
            
            if criteria in score:
                if name not in best_models or score[criteria] < best_models[name][criteria]:
                    best_models[name] = score
        
        # 按criteria排序
        sorted_models = sorted(best_models.items(), key=lambda x: x[1][criteria])
        
        print("模型排名:")
        for i, (name, score) in enumerate(sorted_models[:5]):
            print(f"  {i+1}. {name}: {criteria}={score[criteria]:.2f}")
        
        self.best_models = dict(sorted_models)
        return self.best_models
    
    def create_ensemble_model(self, horizon_type='short_term'):
        """创建集成模型"""
        print(f"正在创建{horizon_type}集成模型...")
        
        if horizon_type not in self.config['model_weights']:
            raise ValueError(f"不支持的时间跨度类型: {horizon_type}")
        
        weights = self.config['model_weights'][horizon_type]
        ensemble_models = {}
        
        for model_name, weight in weights.items():
            if model_name in self.models:
                ensemble_models[model_name] = {
                    'model': self.models[model_name],
                    'weight': weight,
                    'scaler': self.scalers.get(model_name, None)
                }
        
        return ensemble_models
    
    def hyperparameter_tuning(self, X_train, X_val, y_train, y_val, model_name, horizon_type='short_term'):
        """超参数调优"""
        print(f"正在调优 {model_name} 的超参数...")
        
        if model_name not in self.config['hyperparameters']:
            print(f"模型 {model_name} 没有配置超参数")
            return None
        
        param_grid = self.config['hyperparameters'][model_name]
        model = self.create_ffa_models(horizon_type)[model_name]
        
        # 数据标准化
        if model_name in ['Ridge', 'Lasso', 'ElasticNet', 'SVR', 'MLPRegressor']:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
        else:
            X_train_scaled = X_train
            X_val_scaled = X_val
        
        # 时间序列交叉验证
        tscv = TimeSeriesSplit(n_splits=3)
        
        # 网格搜索
        grid_search = GridSearchCV(
            model, param_grid, cv=tscv, scoring='neg_mean_squared_error', n_jobs=-1
        )
        grid_search.fit(X_train_scaled, y_train)
        
        # 更新模型
        self.models[model_name] = grid_search.best_estimator_
        if model_name in ['Ridge', 'Lasso', 'ElasticNet', 'SVR', 'MLPRegressor']:
            self.scalers[model_name] = scaler
        
        print(f"最佳参数: {grid_search.best_params_}")
        print(f"最佳分数: {-grid_search.best_score_:.2f}")
        
        return grid_search.best_estimator_
    
    def get_model(self, name):
        """获取训练好的模型"""
        if name in self.models:
            return self.models[name]
        else:
            raise ValueError(f"模型 {name} 不存在")
    
    def get_scaler(self, name):
        """获取对应的标准化器"""
        return self.scalers.get(name, None)
    
    def predict_ensemble(self, X, ensemble_models):
        """集成预测"""
        predictions = {}
        ensemble_pred = np.zeros(len(X))
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
                
                predictions[model_name] = pred
                ensemble_pred += weight * pred
                total_weight += weight
                
            except Exception as e:
                print(f"模型 {model_name} 预测失败: {e}")
        
        if total_weight > 0:
            ensemble_pred /= total_weight
        
        return ensemble_pred, predictions
    
    def get_feature_importance(self, model_name, feature_names):
        """获取特征重要性"""
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        model = self.models[model_name]
        
        if hasattr(model, 'feature_importances_'):
            # 树模型
            importance = model.feature_importances_
        elif hasattr(model, 'coef_'):
            # 线性模型
            importance = np.abs(model.coef_)
        else:
            return None
        
        feature_importance = dict(zip(feature_names, importance))
        return sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
