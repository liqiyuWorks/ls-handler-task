#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型配置文件 - 定义FFA预测模型的各种配置
"""

# FFA市场配置
FFA_CONFIG = {
    'target_products': ['P4TC', 'C5TC', 'C5'],
    'time_horizons': {
        'short_term': [1, 3, 7],      # 短期预测（天）
        'medium_term': [14, 30, 60],  # 中期预测（天）
        'long_term': [90, 180, 365]   # 长期预测（天）
    },
    'market_seasons': {
        'Q1': [1, 2, 3],    # 第一季度
        'Q2': [4, 5, 6],    # 第二季度
        'Q3': [7, 8, 9],    # 第三季度
        'Q4': [10, 11, 12]  # 第四季度
    }
}

# 特征配置
FEATURE_CONFIG = {
    'price_features': [
        'Price_Mean', 'Price_Std', 'Price_Min', 'Price_Max',
        'Price_Change_1d', 'Price_Change_7d', 'Price_Change_30d',
        'Price_Volatility_7d', 'Price_Volatility_30d'
    ],
    'technical_indicators': [
        'RSI_14', 'MACD', 'Bollinger_Upper', 'Bollinger_Lower',
        'Price_MA_3', 'Price_MA_7', 'Price_MA_14', 'Price_MA_30',
        'Price_MA_3_Std', 'Price_MA_7_Std', 'Price_MA_14_Std', 'Price_MA_30_Std'
    ],
    'time_features': [
        'Year', 'Month', 'Day', 'DayOfWeek', 'IsWeekend', 'Quarter',
        'IsMonthStart', 'IsMonthEnd', 'IsQuarterStart', 'IsQuarterEnd'
    ],
    'commodity_features': [
        'Oil_Price', 'Iron_Ore_Price', 'Coal_Price', 'Steel_Price',
        'Copper_Price', 'Aluminum_Price', 'Zinc_Price'
    ],
    'macro_features': [
        'GDP_Growth', 'Trade_Volume_Index', 'PMI', 'CPI',
        'Interest_Rate', 'USD_Index', 'EUR_USD', 'GBP_USD'
    ],
    'shipping_features': [
        'Vessel_Count', 'Port_Congestion_Index', 'Fleet_Utilization',
        'New_Buildings', 'Scrap_Rate', 'Order_Book'
    ],
    'weather_features': [
        'Wind_Speed', 'Wave_Height', 'Storm_Index', 'Ice_Coverage'
    ],
    'ais_features': [
        'Vessel_Speed', 'Vessel_Density', 'Route_Congestion',
        'Port_Wait_Time', 'Canal_Transit_Time'
    ]
}

# 模型配置
MODEL_CONFIG = {
    'ensemble_models': {
        'linear_models': ['LinearRegression', 'Ridge', 'Lasso', 'ElasticNet'],
        'tree_models': ['RandomForest', 'ExtraTrees', 'GradientBoosting'],
        'neural_models': ['MLPRegressor', 'SVR'],
        'time_series_models': ['ARIMA', 'SARIMAX', 'LSTM']
    },
    'model_weights': {
        'short_term': {
            'LinearRegression': 0.3,
            'Ridge': 0.25,
            'RandomForest': 0.2,
            'GradientBoosting': 0.15,
            'MLPRegressor': 0.1
        },
        'medium_term': {
            'Ridge': 0.3,
            'RandomForest': 0.25,
            'GradientBoosting': 0.2,
            'LinearRegression': 0.15,
            'SVR': 0.1
        },
        'long_term': {
            'RandomForest': 0.35,
            'GradientBoosting': 0.25,
            'Ridge': 0.2,
            'ExtraTrees': 0.15,
            'LinearRegression': 0.05
        }
    },
    'hyperparameters': {
        'Ridge': {'alpha': [0.1, 1.0, 10.0, 100.0]},
        'Lasso': {'alpha': [0.01, 0.1, 1.0, 10.0]},
        'ElasticNet': {'alpha': [0.01, 0.1, 1.0], 'l1_ratio': [0.1, 0.5, 0.9]},
        'RandomForest': {'n_estimators': [100, 200, 300], 'max_depth': [10, 20, None]},
        'GradientBoosting': {'n_estimators': [100, 200], 'learning_rate': [0.01, 0.1, 0.2]},
        'SVR': {'C': [0.1, 1, 10], 'gamma': ['scale', 'auto']}
    }
}

# 评估配置
EVALUATION_CONFIG = {
    'metrics': ['rmse', 'mae', 'r2', 'mape', 'direction_accuracy'],
    'cv_folds': 5,
    'test_size': 0.2,
    'validation_size': 0.2
}

# 预测配置
PREDICTION_CONFIG = {
    'confidence_levels': [0.68, 0.95, 0.99],  # 1σ, 2σ, 3σ
    'max_prediction_days': 365,
    'min_training_samples': 1000
}
