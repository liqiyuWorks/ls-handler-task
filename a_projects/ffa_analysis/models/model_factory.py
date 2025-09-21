#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型工厂 - 创建和训练各种预测模型
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet, LinearRegression
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score, GridSearchCV
# import xgboost as xgb
# import lightgbm as lgb
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
warnings.filterwarnings('ignore')

class ModelFactory:
    """模型工厂类"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.best_models = {}
        self.model_scores = {}
        
    def create_models(self):
        """创建所有可用的模型"""
        models = {
            # 线性模型
            'LinearRegression': LinearRegression(),
            'Ridge': Ridge(alpha=1.0),
            'Lasso': Lasso(alpha=0.1),
            'ElasticNet': ElasticNet(alpha=0.1, l1_ratio=0.5),
            
            # 树模型
            'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            'ExtraTrees': ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            'GradientBoosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            
            # 支持向量机
            'SVR': SVR(kernel='rbf', C=1.0, gamma='scale'),
            
            # 神经网络
            'MLPRegressor': MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42),
            
            # 时间序列模型
            'ARIMA': None,  # 特殊处理
            'SARIMAX': None,  # 特殊处理
        }
        
        # 尝试添加XGBoost和LightGBM
        try:
            import xgboost as xgb
            models['XGBoost'] = xgb.XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        except:
            print("XGBoost不可用，跳过")
            
        try:
            import lightgbm as lgb
            models['LightGBM'] = lgb.LGBMRegressor(n_estimators=100, random_state=42, n_jobs=-1, verbose=-1)
        except:
            print("LightGBM不可用，跳过")
        
        return models
    
    def train_models(self, X_train, X_val, y_train, y_val, model_names=None):
        """训练所有模型"""
        print("正在训练模型...")
        
        if model_names is None:
            model_names = list(self.create_models().keys())
        
        models = self.create_models()
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
                    score = self._train_ml_model(name, models[name], X_train, X_val, y_train, y_val)
                
                results[name] = score
                print(f"  {name} - RMSE: {score['rmse']:.2f}, R²: {score['r2']:.3f}")
                
            except Exception as e:
                print(f"  {name} 训练失败: {e}")
                results[name] = None
        
        self.model_scores = results
        return results
    
    def _train_ml_model(self, name, model, X_train, X_val, y_train, y_val):
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
        
        return {
            'model': model,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape
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
            
            return {
                'model': fitted_model,
                'rmse': rmse,
                'mae': mae,
                'r2': r2,
                'mape': mape
            }
        except Exception as e:
            raise Exception(f"时间序列模型训练失败: {e}")
    
    def select_best_models(self, criteria='rmse'):
        """选择最佳模型"""
        print(f"\n基于 {criteria} 选择最佳模型...")
        
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
    
    def get_model(self, name):
        """获取训练好的模型"""
        if name in self.models:
            return self.models[name]
        else:
            raise ValueError(f"模型 {name} 不存在")
    
    def get_scaler(self, name):
        """获取对应的标准化器"""
        return self.scalers.get(name, None)
    
    def predict(self, X, model_name, days=1):
        """使用指定模型进行预测"""
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        model = self.models[model_name]
        
        if model_name in ['ARIMA', 'SARIMAX']:
            # 时间序列模型
            predictions = model.forecast(days)
        else:
            # 机器学习模型
            if model_name in self.scalers:
                X_scaled = self.scalers[model_name].transform(X)
                predictions = model.predict(X_scaled)
            else:
                predictions = model.predict(X)
        
        return predictions
    
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
    
    def hyperparameter_tuning(self, X_train, X_val, y_train, y_val, model_name, param_grid):
        """超参数调优"""
        print(f"正在调优 {model_name} 的超参数...")
        
        model = self.create_models()[model_name]
        
        # 数据标准化
        if model_name in ['Ridge', 'Lasso', 'ElasticNet', 'SVR', 'MLPRegressor']:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
        else:
            X_train_scaled = X_train
            X_val_scaled = X_val
        
        # 网格搜索
        grid_search = GridSearchCV(
            model, param_grid, cv=3, scoring='neg_mean_squared_error', n_jobs=-1
        )
        grid_search.fit(X_train_scaled, y_train)
        
        # 更新模型
        self.models[model_name] = grid_search.best_estimator_
        if model_name in ['Ridge', 'Lasso', 'ElasticNet', 'SVR', 'MLPRegressor']:
            self.scalers[model_name] = scaler
        
        print(f"最佳参数: {grid_search.best_params_}")
        print(f"最佳分数: {-grid_search.best_score_:.2f}")
        
        return grid_search.best_estimator_
