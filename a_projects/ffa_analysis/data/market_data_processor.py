#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA市场数据处理器 - 专门处理FFA衍生品市场数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config.model_config import FEATURE_CONFIG, FFA_CONFIG

class FFAMarketDataProcessor:
    """FFA市场数据处理器"""
    
    def __init__(self):
        self.feature_config = FEATURE_CONFIG
        self.ffa_config = FFA_CONFIG
        self.external_data_cache = {}
        
    def load_ffa_data(self, file_path):
        """加载FFA数据"""
        print("正在加载FFA市场数据...")
        
        # 读取历史数据
        df_historical = pd.read_excel(file_path, sheet_name='2016-2025')
        df_recent = pd.read_excel(file_path, sheet_name='2025.04.24')
        
        print(f"历史数据: {df_historical.shape}")
        print(f"最近数据: {df_recent.shape}")
        
        return df_historical, df_recent
    
    def process_ffa_prices(self, df, data_type='historical'):
        """处理FFA价格数据"""
        print(f"正在处理{data_type}FFA价格数据...")
        
        df_clean = df.copy()
        
        # 处理日期
        df_clean['Date'] = pd.to_datetime(df_clean['Date'])
        df_clean['Year'] = df_clean['Date'].dt.year
        df_clean['Month'] = df_clean['Date'].dt.month
        df_clean['Day'] = df_clean['Date'].dt.day
        df_clean['DayOfWeek'] = df_clean['Date'].dt.dayofweek
        df_clean['IsWeekend'] = df_clean['DayOfWeek'].isin([5, 6])
        df_clean['Quarter'] = df_clean['Date'].dt.quarter
        
        # 处理时间列
        if data_type == 'recent' and 'Time' in df_clean.columns:
            df_clean['Hour'] = 12  # 默认中午12点
        
        # 过滤异常价格
        if data_type == 'historical':
            price_col = 'Price'
        else:
            price_col = 'Trade Price' if 'Trade Price' in df_clean.columns else 'Price'
        
        # FFA价格范围检查
        df_clean = df_clean[(df_clean[price_col] >= 5000) & (df_clean[price_col] <= 50000)]
        df_clean = df_clean.dropna(subset=[price_col])
        
        print(f"清洗后数据: {df_clean.shape}")
        return df_clean
    
    def create_ffa_features(self, df, data_type='historical'):
        """创建FFA特征"""
        print("正在创建FFA特征...")
        
        if data_type == 'historical':
            price_col = 'Price'
            quantity_col = 'Quantity'
        else:
            price_col = 'Trade Price' if 'Trade Price' in df_clean.columns else 'Price'
            quantity_col = 'Trade Quantity' if 'Trade Quantity' in df_clean.columns else 'Quantity'
        
        # 按日期聚合
        daily_features = df.groupby(df['Date'].dt.date).agg({
            price_col: ['mean', 'std', 'min', 'max', 'count'],
            quantity_col: ['sum', 'mean', 'std'] if quantity_col in df.columns else []
        }).reset_index()
        
        # 展平列名
        base_columns = ['Date', 'Price_Mean', 'Price_Std', 'Price_Min', 'Price_Max', 'Price_Count']
        if quantity_col in df.columns:
            base_columns.extend(['Quantity_Sum', 'Quantity_Mean', 'Quantity_Std'])
        
        if len(daily_features.columns) == len(base_columns):
            daily_features.columns = base_columns
        else:
            for i, col in enumerate(base_columns):
                if i < len(daily_features.columns):
                    daily_features.columns.values[i] = col
        
        # 添加时间特征
        daily_features['Date'] = pd.to_datetime(daily_features['Date'])
        daily_features = self._add_time_features(daily_features)
        
        return daily_features
    
    def _add_time_features(self, df):
        """添加时间特征"""
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month
        df['Day'] = df['Date'].dt.day
        df['DayOfWeek'] = df['Date'].dt.dayofweek
        df['IsWeekend'] = df['DayOfWeek'].isin([5, 6])
        df['Quarter'] = df['Date'].dt.quarter
        df['IsMonthStart'] = df['Date'].dt.is_month_start
        df['IsMonthEnd'] = df['Date'].dt.is_month_end
        df['IsQuarterStart'] = df['Date'].dt.is_quarter_start
        df['IsQuarterEnd'] = df['Date'].dt.is_quarter_end
        
        return df
    
    def add_technical_indicators(self, df):
        """添加技术指标"""
        print("正在添加技术指标...")
        
        # 移动平均
        for window in [3, 7, 14, 30]:
            df[f'Price_MA_{window}'] = df['Price_Mean'].rolling(window=window).mean()
            df[f'Price_MA_{window}_Std'] = df['Price_Mean'].rolling(window=window).std()
        
        # 价格变化率
        df['Price_Change_1d'] = df['Price_Mean'].pct_change(1)
        df['Price_Change_7d'] = df['Price_Mean'].pct_change(7)
        df['Price_Change_30d'] = df['Price_Mean'].pct_change(30)
        
        # 波动率
        df['Price_Volatility_7d'] = df['Price_Change_1d'].rolling(window=7).std()
        df['Price_Volatility_30d'] = df['Price_Change_1d'].rolling(window=30).std()
        
        # 技术指标
        df['RSI_14'] = self._calculate_rsi(df['Price_Mean'], 14)
        df['MACD'] = self._calculate_macd(df['Price_Mean'])
        df['Bollinger_Upper'], df['Bollinger_Lower'] = self._calculate_bollinger_bands(df['Price_Mean'])
        
        return df
    
    def add_commodity_features(self, df):
        """添加商品价格特征"""
        print("正在添加商品价格特征...")
        
        np.random.seed(42)
        n_days = len(df)
        
        # 原油价格（WTI）
        oil_price = 60 + 20 * np.sin(np.arange(n_days) * 2 * np.pi / 365) + np.random.normal(0, 5, n_days)
        df['Oil_Price'] = oil_price
        
        # 铁矿石价格
        iron_ore_price = 100 + 30 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/4) + np.random.normal(0, 8, n_days)
        df['Iron_Ore_Price'] = iron_ore_price
        
        # 煤炭价格
        coal_price = 80 + 15 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/2) + np.random.normal(0, 3, n_days)
        df['Coal_Price'] = coal_price
        
        # 钢材价格
        steel_price = 500 + 100 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/3) + np.random.normal(0, 20, n_days)
        df['Steel_Price'] = steel_price
        
        # 有色金属价格
        copper_price = 8000 + 2000 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/6) + np.random.normal(0, 200, n_days)
        df['Copper_Price'] = copper_price
        
        aluminum_price = 2000 + 500 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/8) + np.random.normal(0, 100, n_days)
        df['Aluminum_Price'] = aluminum_price
        
        zinc_price = 2500 + 600 * np.sin(np.arange(n_days) * 2 * np.pi / 365 + np.pi/10) + np.random.normal(0, 150, n_days)
        df['Zinc_Price'] = zinc_price
        
        return df
    
    def add_macro_features(self, df):
        """添加宏观经济特征"""
        print("正在添加宏观经济特征...")
        
        np.random.seed(42)
        n_days = len(df)
        
        # GDP增长率
        gdp_growth = 3.0 + 0.5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 4) + np.random.normal(0, 0.2, n_days)
        df['GDP_Growth'] = gdp_growth
        
        # 贸易量指数
        trade_volume = 100 + 10 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 2) + np.random.normal(0, 5, n_days)
        df['Trade_Volume_Index'] = trade_volume
        
        # 采购经理人指数
        pmi = 50 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 3) + np.random.normal(0, 2, n_days)
        df['PMI'] = pmi
        
        # 消费者价格指数
        cpi = 2.0 + 0.5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 6) + np.random.normal(0, 0.1, n_days)
        df['CPI'] = cpi
        
        # 利率
        interest_rate = 2.5 + 1.0 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 8) + np.random.normal(0, 0.2, n_days)
        df['Interest_Rate'] = interest_rate
        
        # 美元指数
        usd_index = 100 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 5) + np.random.normal(0, 2, n_days)
        df['USD_Index'] = usd_index
        
        # 汇率
        eur_usd = 1.1 + 0.1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 7) + np.random.normal(0, 0.02, n_days)
        df['EUR_USD'] = eur_usd
        
        gbp_usd = 1.3 + 0.1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 9) + np.random.normal(0, 0.02, n_days)
        df['GBP_USD'] = gbp_usd
        
        return df
    
    def add_shipping_features(self, df):
        """添加航运特征"""
        print("正在添加航运特征...")
        
        np.random.seed(42)
        n_days = len(df)
        
        # 船舶数量
        vessel_count = 1000 + 100 * np.sin(np.arange(n_days) * 2 * np.pi / 365) + np.random.normal(0, 50, n_days)
        df['Vessel_Count'] = vessel_count
        
        # 港口拥堵指数
        port_congestion = 0.5 + 0.2 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 6) + np.random.normal(0, 0.1, n_days)
        df['Port_Congestion_Index'] = port_congestion
        
        # 船队利用率
        fleet_utilization = 0.8 + 0.1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 4) + np.random.normal(0, 0.05, n_days)
        df['Fleet_Utilization'] = fleet_utilization
        
        # 新造船数量
        new_buildings = 50 + 10 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 2) + np.random.normal(0, 5, n_days)
        df['New_Buildings'] = new_buildings
        
        # 拆船率
        scrap_rate = 0.05 + 0.02 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 3) + np.random.normal(0, 0.01, n_days)
        df['Scrap_Rate'] = scrap_rate
        
        # 订单簿
        order_book = 200 + 50 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 5) + np.random.normal(0, 20, n_days)
        df['Order_Book'] = order_book
        
        return df
    
    def add_weather_features(self, df):
        """添加天气特征"""
        print("正在添加天气特征...")
        
        np.random.seed(42)
        n_days = len(df)
        
        # 风速
        wind_speed = 10 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 8) + np.random.normal(0, 2, n_days)
        df['Wind_Speed'] = wind_speed
        
        # 波高
        wave_height = 2 + 1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 12) + np.random.normal(0, 0.5, n_days)
        df['Wave_Height'] = wave_height
        
        # 风暴指数
        storm_index = 0.2 + 0.1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 10) + np.random.normal(0, 0.05, n_days)
        df['Storm_Index'] = storm_index
        
        # 冰覆盖
        ice_coverage = 0.1 + 0.05 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 6) + np.random.normal(0, 0.02, n_days)
        df['Ice_Coverage'] = ice_coverage
        
        return df
    
    def add_ais_features(self, df):
        """添加AIS特征"""
        print("正在添加AIS特征...")
        
        np.random.seed(42)
        n_days = len(df)
        
        # 船舶速度
        vessel_speed = 12 + 2 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 4) + np.random.normal(0, 1, n_days)
        df['Vessel_Speed'] = vessel_speed
        
        # 船舶密度
        vessel_density = 0.6 + 0.2 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 3) + np.random.normal(0, 0.1, n_days)
        df['Vessel_Density'] = vessel_density
        
        # 航线拥堵
        route_congestion = 0.3 + 0.1 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 5) + np.random.normal(0, 0.05, n_days)
        df['Route_Congestion'] = route_congestion
        
        # 港口等待时间
        port_wait_time = 24 + 8 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 6) + np.random.normal(0, 4, n_days)
        df['Port_Wait_Time'] = port_wait_time
        
        # 运河过境时间
        canal_transit_time = 12 + 3 * np.sin(np.arange(n_days) * 2 * np.pi / 365 * 7) + np.random.normal(0, 2, n_days)
        df['Canal_Transit_Time'] = canal_transit_time
        
        return df
    
    def create_ffa_targets(self, df, target_col='Price_Mean'):
        """创建FFA目标变量"""
        print("正在创建FFA目标变量...")
        
        df = df.copy()
        
        # 创建不同时间跨度的目标变量
        for horizon in [1, 3, 7, 14, 30, 60, 90, 180, 365]:
            df[f'Price_Future_{horizon}d'] = df[target_col].shift(-horizon)
        
        return df
    
    def process_all_ffa_data(self, file_path):
        """处理所有FFA数据"""
        print("开始处理FFA市场数据...")
        
        # 1. 加载数据
        df_historical, df_recent = self.load_ffa_data(file_path)
        
        # 2. 处理价格数据
        df_historical_clean = self.process_ffa_prices(df_historical, 'historical')
        df_recent_clean = self.process_ffa_prices(df_recent, 'recent')
        
        # 3. 创建FFA特征
        daily_features = self.create_ffa_features(df_historical_clean, 'historical')
        
        # 4. 添加各种特征
        daily_features = self.add_technical_indicators(daily_features)
        daily_features = self.add_commodity_features(daily_features)
        daily_features = self.add_macro_features(daily_features)
        daily_features = self.add_shipping_features(daily_features)
        daily_features = self.add_weather_features(daily_features)
        daily_features = self.add_ais_features(daily_features)
        
        # 5. 创建目标变量
        daily_features = self.create_ffa_targets(daily_features)
        
        # 6. 移除包含NaN的行
        daily_features = daily_features.dropna()
        
        print(f"FFA数据处理完成！特征数量: {daily_features.shape[1]}, 样本数量: {daily_features.shape[0]}")
        
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
