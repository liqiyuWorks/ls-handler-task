#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理器 - 数据加载、清洗、特征工程
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class DataProcessor:
    """数据处理器"""
    
    def __init__(self):
        self.feature_columns = []
        self.scaler = None
        
    def load_data(self, file_path):
        """加载数据"""
        print("正在加载数据...")
        
        # 读取历史数据
        df_historical = pd.read_excel(file_path, sheet_name='2016-2025')
        df_recent = pd.read_excel(file_path, sheet_name='2025.04.24')
        
        print(f"历史数据: {df_historical.shape}")
        print(f"最近数据: {df_recent.shape}")
        
        return df_historical, df_recent
    
    def clean_data(self, df, data_type='historical'):
        """清洗数据"""
        print(f"正在清洗{data_type}数据...")
        
        df_clean = df.copy()
        
        # 处理日期
        df_clean['Date'] = pd.to_datetime(df_clean['Date'])
        df_clean['Year'] = df_clean['Date'].dt.year
        df_clean['Month'] = df_clean['Date'].dt.month
        df_clean['Day'] = df_clean['Date'].dt.day
        df_clean['DayOfWeek'] = df_clean['Date'].dt.dayofweek
        df_clean['IsWeekend'] = df_clean['DayOfWeek'].isin([5, 6])
        df_clean['Quarter'] = df_clean['Date'].dt.quarter
        
        # 处理时间列（如果是recent数据）
        if data_type == 'recent' and 'Time' in df_clean.columns:
            df_clean['Hour'] = 12  # 默认中午12点
        
        # 过滤异常价格
        if data_type == 'historical':
            df_clean = df_clean[(df_clean['Price'] >= 1000) & (df_clean['Price'] <= 100000)]
        else:
            price_col = 'Trade Price' if 'Trade Price' in df_clean.columns else 'Price'
            df_clean = df_clean[(df_clean[price_col] >= 1000) & (df_clean[price_col] <= 100000)]
        
        # 处理缺失值
        price_col = 'Price' if data_type == 'historical' else 'Trade Price'
        df_clean = df_clean.dropna(subset=[price_col])
        
        print(f"清洗后数据: {df_clean.shape}")
        return df_clean
    
    def create_daily_features(self, df, data_type='historical'):
        """创建日度特征"""
        print("正在创建日度特征...")
        
        if data_type == 'historical':
            price_col = 'Price'
            quantity_col = 'Quantity'
        else:
            price_col = 'Trade Price'
            quantity_col = 'Trade Quantity'
        
        # 按日期聚合
        daily_features = df.groupby(df['Date'].dt.date).agg({
            price_col: ['mean', 'std', 'min', 'max', 'count'],
            quantity_col: ['sum', 'mean', 'std'] if quantity_col in df.columns else []
        }).reset_index()
        
        # 展平列名
        base_columns = ['Date', 'Price_Mean', 'Price_Std', 'Price_Min', 'Price_Max', 'Price_Count']
        if quantity_col in df.columns:
            base_columns.extend(['Quantity_Sum', 'Quantity_Mean', 'Quantity_Std'])
        
        # 确保列名数量匹配
        if len(daily_features.columns) == len(base_columns):
            daily_features.columns = base_columns
        else:
            for i, col in enumerate(base_columns):
                if i < len(daily_features.columns):
                    daily_features.columns.values[i] = col
        
        # 添加时间特征
        daily_features['Date'] = pd.to_datetime(daily_features['Date'])
        daily_features['Year'] = daily_features['Date'].dt.year
        daily_features['Month'] = daily_features['Date'].dt.month
        daily_features['Day'] = daily_features['Date'].dt.day
        daily_features['DayOfWeek'] = daily_features['Date'].dt.dayofweek
        daily_features['IsWeekend'] = daily_features['DayOfWeek'].isin([5, 6])
        daily_features['Quarter'] = daily_features['Date'].dt.quarter
        
        return daily_features
    
    def add_technical_indicators(self, daily_features):
        """添加技术指标"""
        print("正在添加技术指标...")
        
        # 添加滞后特征
        for lag in [1, 3, 7, 14, 30]:
            daily_features[f'Price_Mean_Lag_{lag}'] = daily_features['Price_Mean'].shift(lag)
            daily_features[f'Price_Std_Lag_{lag}'] = daily_features['Price_Std'].shift(lag)
        
        # 添加移动平均特征
        for window in [3, 7, 14, 30]:
            daily_features[f'Price_MA_{window}'] = daily_features['Price_Mean'].rolling(window=window).mean()
            daily_features[f'Price_MA_{window}_Std'] = daily_features['Price_Mean'].rolling(window=window).std()
        
        # 添加价格变化率特征
        daily_features['Price_Change_1d'] = daily_features['Price_Mean'].pct_change(1)
        daily_features['Price_Change_7d'] = daily_features['Price_Mean'].pct_change(7)
        daily_features['Price_Change_30d'] = daily_features['Price_Mean'].pct_change(30)
        
        # 添加波动率特征
        daily_features['Price_Volatility_7d'] = daily_features['Price_Change_1d'].rolling(window=7).std()
        daily_features['Price_Volatility_30d'] = daily_features['Price_Change_1d'].rolling(window=30).std()
        
        # 添加技术指标
        daily_features['RSI_14'] = self._calculate_rsi(daily_features['Price_Mean'], 14)
        daily_features['MACD'] = self._calculate_macd(daily_features['Price_Mean'])
        daily_features['Bollinger_Upper'] = self._calculate_bollinger_bands(daily_features['Price_Mean'], 20, 2)[0]
        daily_features['Bollinger_Lower'] = self._calculate_bollinger_bands(daily_features['Price_Mean'], 20, 2)[1]
        
        return daily_features
    
    def add_external_features(self, daily_features):
        """添加外部特征"""
        print("正在添加外部特征...")
        
        np.random.seed(42)
        n_days = len(daily_features)
        
        # 模拟商品价格数据
        oil_price = 60 + 20 * np.sin(np.arange(n_days) * 2 * np.pi / 365) + np.random.normal(0, 5, n_days)
        daily_features['Oil_Price'] = oil_price
        
        iron_ore_price = 100 + 30 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/4) + np.random.normal(0, 8, n_days)
        daily_features['Iron_Ore_Price'] = iron_ore_price
        
        coal_price = 80 + 15 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/2) + np.random.normal(0, 3, n_days)
        daily_features['Coal_Price'] = coal_price
        
        # 宏观经济指标
        daily_features['GDP_Growth'] = 3.0 + 0.5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 4) + np.random.normal(0, 0.2, n_days)
        daily_features['Trade_Volume_Index'] = 100 + 10 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 2) + np.random.normal(0, 5, n_days)
        daily_features['PMI'] = 50 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 3) + np.random.normal(0, 2, n_days)
        
        # AIS相关指标（模拟）
        daily_features['Vessel_Count'] = 1000 + 100 * np.sin(np.arange(n_days) * 2 * np.pi / 365) + np.random.normal(0, 50, n_days)
        daily_features['Port_Congestion_Index'] = 0.5 + 0.2 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 6) + np.random.normal(0, 0.1, n_days)
        
        # 天气指标
        daily_features['Wind_Speed'] = 10 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 8) + np.random.normal(0, 2, n_days)
        daily_features['Wave_Height'] = 2 + 1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 12) + np.random.normal(0, 0.5, n_days)
        
        return daily_features
    
    def _calculate_rsi(self, prices, window=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        return macd
    
    def _calculate_bollinger_bands(self, prices, window=20, num_std=2):
        """计算布林带"""
        rolling_mean = prices.rolling(window=window).mean()
        rolling_std = prices.rolling(window=window).std()
        upper_band = rolling_mean + (rolling_std * num_std)
        lower_band = rolling_mean - (rolling_std * num_std)
        return upper_band, lower_band
    
    def prepare_training_data(self, daily_features, target_col='Price_Mean'):
        """准备训练数据"""
        print("正在准备训练数据...")
        
        # 移除包含NaN的行
        daily_features = daily_features.dropna()
        
        # 选择特征列
        feature_cols = [col for col in daily_features.columns if col not in ['Date', target_col]]
        self.feature_columns = feature_cols
        
        # 创建目标变量
        daily_features = daily_features.copy()
        daily_features['Price_Future_1d'] = daily_features[target_col].shift(-1)
        daily_features['Price_Future_7d'] = daily_features[target_col].shift(-7)
        daily_features['Price_Future_30d'] = daily_features[target_col].shift(-30)
        
        # 移除包含NaN的行
        daily_features = daily_features.dropna()
        
        # 分离特征和目标
        X = daily_features[feature_cols]
        y_1d = daily_features['Price_Future_1d']
        y_7d = daily_features['Price_Future_7d']
        y_30d = daily_features['Price_Future_30d']
        
        return X, y_1d, y_7d, y_30d, daily_features
    
    def process_all(self, file_path):
        """完整的处理流程"""
        print("开始数据处理...")
        
        # 1. 加载数据
        df_historical, df_recent = self.load_data(file_path)
        
        # 2. 清洗数据
        df_historical_clean = self.clean_data(df_historical, 'historical')
        df_recent_clean = self.clean_data(df_recent, 'recent')
        
        # 3. 创建日度特征
        daily_features = self.create_daily_features(df_historical_clean, 'historical')
        
        # 4. 添加技术指标
        daily_features = self.add_technical_indicators(daily_features)
        
        # 5. 添加外部特征
        daily_features = self.add_external_features(daily_features)
        
        # 6. 准备训练数据
        X, y_1d, y_7d, y_30d, daily_features = self.prepare_training_data(daily_features)
        
        print(f"数据处理完成！特征数量: {X.shape[1]}, 样本数量: {X.shape[0]}")
        
        return X, y_1d, y_7d, y_30d, daily_features
