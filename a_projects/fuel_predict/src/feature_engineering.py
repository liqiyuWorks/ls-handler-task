#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测特征工程模块
基于航运行业知识的特征提取和工程化

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder, PolynomialFeatures
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
import warnings
warnings.filterwarnings('ignore')

from .cp_clause_definitions import CPClauseCalculator, ShipType, LoadCondition, IndustryStandards

class ShipFuelFeatureEngineer:
    """船舶油耗特征工程器"""
    
    def __init__(self):
        """初始化特征工程器"""
        self.cp_calculator = CPClauseCalculator()
        self.scalers = {}
        self.encoders = {}
        self.feature_names = []
        self.selected_features = []
        
    def extract_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取基础特征"""
        df_features = df.copy()
        
        # 1. 时间特征
        df_features['报告时间'] = pd.to_datetime(df_features['报告时间'], unit='ms', errors='coerce')
        df_features['hour'] = df_features['报告时间'].dt.hour
        df_features['day_of_week'] = df_features['报告时间'].dt.dayofweek
        df_features['month'] = df_features['报告时间'].dt.month
        df_features['season'] = df_features['month'].apply(self._get_season)
        
        # 2. 基础性能指标
        df_features['总油耗(mt)'] = df_features['重油IFO(mt)'] + df_features['轻油MDO/MGO(mt)']
        
        # 避免除零错误
        df_features['小时油耗(mt/h)'] = np.where(
            df_features['航行时间(hrs)'] > 0,
            df_features['总油耗(mt)'] / df_features['航行时间(hrs)'],
            0
        )
        
        df_features['单位距离油耗(mt/nm)'] = np.where(
            df_features['航行距离(nm)'] > 0,
            df_features['总油耗(mt)'] / df_features['航行距离(nm)'],
            0
        )
        
        df_features['燃油效率'] = np.where(
            df_features['总油耗(mt)'] > 0,
            df_features['航行距离(nm)'] / df_features['总油耗(mt)'],
            0
        )
        
        # 3. 船舶特征
        df_features['载重比'] = df_features['船舶吃水(m)'] / (df_features['船舶载重(t)'] / 10000)
        df_features['长宽比'] = df_features['船舶总长度(m)'] / np.sqrt(df_features['船舶载重(t)'])
        df_features['船舶年龄'] = df_features['船龄'].fillna(df_features['船龄'].median())
        
        # 4. 速度相关特征
        df_features['速度平方'] = df_features['平均速度(kts)'] ** 2
        df_features['速度立方'] = df_features['平均速度(kts)'] ** 3
        
        # 5. CP条款偏差特征
        df_features['速度偏差'] = df_features['平均速度(kts)'] - df_features['航速cp']
        df_features['速度偏差率'] = np.where(
            df_features['航速cp'] > 0,
            (df_features['平均速度(kts)'] - df_features['航速cp']) / df_features['航速cp'],
            0
        )
        
        return df_features
    
    def extract_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取高级特征"""
        df_advanced = df.copy()
        
        # 1. 船舶分类特征
        df_advanced['dwt_category'] = df_advanced.apply(
            lambda x: self._get_dwt_category(x['船舶类型'], x['船舶载重(t)']), axis=1
        )
        
        # 2. 海军系数 (Admiralty Coefficient) 估算
        # 使用经验公式估算主机功率
        df_advanced['estimated_power'] = df_advanced.apply(
            lambda x: self._estimate_main_engine_power(x['船舶类型'], x['船舶载重(t)']), axis=1
        )
        
        df_advanced['admiralty_coefficient'] = df_advanced.apply(
            lambda x: IndustryStandards.calculate_admiralty_coefficient(
                x['平均速度(kts)'], x['estimated_power'], x['船舶载重(t)']
            ) if x['平均速度(kts)'] > 0 and x['estimated_power'] > 0 else 0, axis=1
        )
        
        # 3. 载重状态数值化
        df_advanced['load_factor'] = df_advanced['载重状态'].map({
            'Laden': 1.0,
            'Ballast': 0.0,
            'Part Laden': 0.5
        }).fillna(0.5)
        
        # 4. 航行效率指标
        df_advanced['distance_per_hour'] = np.where(
            df_advanced['航行时间(hrs)'] > 0,
            df_advanced['航行距离(nm)'] / df_advanced['航行时间(hrs)'],
            0
        )
        
        # 5. 燃料比例特征
        df_advanced['heavy_fuel_ratio'] = np.where(
            df_advanced['总油耗(mt)'] > 0,
            df_advanced['重油IFO(mt)'] / df_advanced['总油耗(mt)'],
            0
        )
        
        # 6. 相对性能指标
        df_advanced = self._add_relative_performance_features(df_advanced)
        
        # 7. 交互特征
        df_advanced = self._add_interaction_features(df_advanced)
        
        return df_advanced
    
    def _get_season(self, month: int) -> str:
        """根据月份获取季节"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'
    
    def _get_dwt_category(self, ship_type: str, dwt: float) -> str:
        """根据船型和载重吨位获取分类"""
        # 处理可能的NaN或非字符串类型
        if not isinstance(ship_type, str) or pd.isna(ship_type):
            return 'Other'
        
        ship_type_upper = str(ship_type).upper()
        
        if 'BULK' in ship_type_upper:
            categories = IndustryStandards.get_dwt_categories()
            for category, (min_dwt, max_dwt) in categories.items():
                if min_dwt <= dwt < max_dwt:
                    return category
        elif 'CONTAINER' in ship_type_upper:
            # 简化处理，假设TEU约为DWT的1/14
            teu = dwt / 14
            categories = IndustryStandards.get_container_ship_categories()
            for category, (min_teu, max_teu) in categories.items():
                if min_teu <= teu < max_teu:
                    return category
        elif 'TANKER' in ship_type_upper:
            categories = IndustryStandards.get_tanker_categories()
            for category, (min_dwt, max_dwt) in categories.items():
                if min_dwt <= dwt < max_dwt:
                    return category
        
        return 'Other'
    
    def _estimate_main_engine_power(self, ship_type: str, dwt: float) -> float:
        """估算主机功率 (kW)"""
        # 处理可能的NaN或非字符串类型
        if not isinstance(ship_type, str) or pd.isna(ship_type):
            return dwt * 0.25  # 默认值
        
        ship_type_upper = str(ship_type).upper()
        
        # 基于经验公式的主机功率估算
        if 'BULK' in ship_type_upper:
            return dwt * 0.15  # 散货船约0.15 kW/DWT
        elif 'CONTAINER' in ship_type_upper:
            return dwt * 0.8   # 集装箱船约0.8 kW/DWT
        elif 'TANKER' in ship_type_upper:
            return dwt * 0.2   # 油轮约0.2 kW/DWT
        else:
            return dwt * 0.25  # 其他船型约0.25 kW/DWT
    
    def _add_relative_performance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加相对性能特征"""
        # 按船型计算相对性能
        for ship_type in df['船舶类型'].unique():
            mask = df['船舶类型'] == ship_type
            ship_data = df[mask]
            
            if len(ship_data) > 5:  # 确保有足够的数据
                # 相对速度 (相对于同船型平均值)
                mean_speed = ship_data['平均速度(kts)'].mean()
                df.loc[mask, 'relative_speed'] = df.loc[mask, '平均速度(kts)'] / mean_speed
                
                # 相对油耗
                mean_consumption = ship_data['小时油耗(mt/h)'].mean()
                if mean_consumption > 0:
                    df.loc[mask, 'relative_consumption'] = df.loc[mask, '小时油耗(mt/h)'] / mean_consumption
                else:
                    df.loc[mask, 'relative_consumption'] = 1.0
        
        # 填充缺失值
        if 'relative_speed' not in df.columns:
            df['relative_speed'] = 1.0
        else:
            df['relative_speed'] = df['relative_speed'].fillna(1.0)
            
        if 'relative_consumption' not in df.columns:
            df['relative_consumption'] = 1.0
        else:
            df['relative_consumption'] = df['relative_consumption'].fillna(1.0)
        
        return df
    
    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加交互特征"""
        # 速度与载重状态的交互
        df['speed_load_interaction'] = df['平均速度(kts)'] * df['load_factor']
        
        # 船舶大小与速度的交互
        df['size_speed_interaction'] = df['船舶载重(t)'] * df['平均速度(kts)'] / 100000
        
        # 天气因子 (基于速度偏差估算)
        df['weather_factor'] = np.where(
            df['速度偏差率'].abs() > 0.1,
            1.0 + df['速度偏差率'].abs(),
            1.0
        )
        
        # 载重与吃水的交互
        df['dwt_draft_interaction'] = df['船舶载重(t)'] * df['船舶吃水(m)'] / 100000
        
        return df
    
    def encode_categorical_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """编码分类特征"""
        df_encoded = df.copy()
        
        categorical_features = ['船舶类型', '载重状态', '报告类型', 'dwt_category', 'season']
        
        for feature in categorical_features:
            if feature in df_encoded.columns:
                if fit:
                    if feature not in self.encoders:
                        self.encoders[feature] = LabelEncoder()
                    df_encoded[f'{feature}_encoded'] = self.encoders[feature].fit_transform(
                        df_encoded[feature].astype(str)
                    )
                else:
                    if feature in self.encoders:
                        # 处理未见过的类别
                        unique_values = df_encoded[feature].astype(str).unique()
                        known_values = self.encoders[feature].classes_
                        
                        # 将未知类别映射到最常见的类别
                        df_encoded[feature] = df_encoded[feature].astype(str).apply(
                            lambda x: x if x in known_values else known_values[0]
                        )
                        
                        df_encoded[f'{feature}_encoded'] = self.encoders[feature].transform(
                            df_encoded[feature]
                        )
        
        return df_encoded
    
    def scale_numerical_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """标准化数值特征"""
        df_scaled = df.copy()
        
        # 选择需要标准化的数值特征
        numerical_features = [
            '船舶载重(t)', '船舶吃水(m)', '船舶总长度(m)', '平均速度(kts)',
            '航行距离(nm)', '航行时间(hrs)', '载重比', '长宽比', '船舶年龄',
            '速度平方', '速度立方', 'estimated_power', 'admiralty_coefficient',
            'distance_per_hour', 'size_speed_interaction', 'dwt_draft_interaction'
        ]
        
        # 只选择存在的特征
        existing_features = [f for f in numerical_features if f in df_scaled.columns]
        
        if fit:
            for feature in existing_features:
                if feature not in self.scalers:
                    self.scalers[feature] = StandardScaler()
                
                # 处理无穷大和NaN值
                df_scaled[feature] = df_scaled[feature].replace([np.inf, -np.inf], np.nan)
                df_scaled[feature] = df_scaled[feature].fillna(df_scaled[feature].median())
                
                df_scaled[f'{feature}_scaled'] = self.scalers[feature].fit_transform(
                    df_scaled[[feature]]
                ).flatten()
        else:
            for feature in existing_features:
                if feature in self.scalers:
                    # 处理无穷大和NaN值
                    df_scaled[feature] = df_scaled[feature].replace([np.inf, -np.inf], np.nan)
                    df_scaled[feature] = df_scaled[feature].fillna(0)  # 测试时用0填充
                    
                    df_scaled[f'{feature}_scaled'] = self.scalers[feature].transform(
                        df_scaled[[feature]]
                    ).flatten()
        
        return df_scaled
    
    def select_features(self, df: pd.DataFrame, target_col: str, k: int = 20) -> List[str]:
        """特征选择"""
        # 获取所有特征列
        feature_cols = [col for col in df.columns if 
                       col not in ['报告时间', target_col] and 
                       not col.startswith('MMSI') and 
                       not col.startswith('IMO') and
                       not col.startswith('航次ID')]
        
        # 移除非数值特征
        numerical_cols = []
        for col in feature_cols:
            if df[col].dtype in ['int64', 'float64']:
                if not df[col].isna().all() and df[col].var() > 1e-10:
                    numerical_cols.append(col)
        
        if len(numerical_cols) == 0:
            return []
        
        # 准备数据
        X = df[numerical_cols].fillna(0)
        y = df[target_col].fillna(0)
        
        # 移除目标变量为0的样本
        valid_mask = (y > 0) & (y < y.quantile(0.99))  # 移除异常值
        X = X[valid_mask]
        y = y[valid_mask]
        
        if len(X) == 0:
            return numerical_cols[:k]
        
        # 特征选择
        try:
            # 使用互信息进行特征选择
            selector = SelectKBest(score_func=mutual_info_regression, k=min(k, len(numerical_cols)))
            selector.fit(X, y)
            
            selected_features = [numerical_cols[i] for i in selector.get_support(indices=True)]
            self.selected_features = selected_features
            
            return selected_features
        except Exception as e:
            print(f"特征选择失败: {e}")
            return numerical_cols[:k]
    
    def create_polynomial_features(self, df: pd.DataFrame, feature_cols: List[str], 
                                 degree: int = 2) -> pd.DataFrame:
        """创建多项式特征"""
        if len(feature_cols) == 0:
            return df
        
        df_poly = df.copy()
        
        # 选择关键特征进行多项式扩展
        key_features = ['平均速度(kts)', '船舶载重(t)', 'load_factor']
        poly_features = [f for f in key_features if f in feature_cols]
        
        if len(poly_features) >= 2:
            try:
                X_poly = df[poly_features].fillna(0)
                
                poly = PolynomialFeatures(degree=degree, interaction_only=True, 
                                        include_bias=False)
                X_poly_transformed = poly.fit_transform(X_poly)
                
                # 获取特征名称
                poly_feature_names = poly.get_feature_names_out(poly_features)
                
                # 添加多项式特征
                for i, name in enumerate(poly_feature_names):
                    if name not in poly_features:  # 跳过原始特征
                        df_poly[f'poly_{name}'] = X_poly_transformed[:, i]
                
            except Exception as e:
                print(f"多项式特征创建失败: {e}")
        
        return df_poly
    
    def engineer_features(self, df: pd.DataFrame, target_col: str = '小时油耗(mt/h)', 
                         fit: bool = True) -> pd.DataFrame:
        """完整的特征工程流程"""
        print("开始特征工程...")
        
        # 1. 提取基础特征
        print("提取基础特征...")
        df_features = self.extract_basic_features(df)
        
        # 2. 提取高级特征
        print("提取高级特征...")
        df_features = self.extract_advanced_features(df_features)
        
        # 3. 编码分类特征
        print("编码分类特征...")
        df_features = self.encode_categorical_features(df_features, fit=fit)
        
        # 4. 标准化数值特征
        print("标准化数值特征...")
        df_features = self.scale_numerical_features(df_features, fit=fit)
        
        # 5. 特征选择
        if fit:
            print("进行特征选择...")
            selected_features = self.select_features(df_features, target_col, k=25)
            print(f"选择了 {len(selected_features)} 个特征")
        
        # 6. 创建多项式特征
        if fit and hasattr(self, 'selected_features'):
            print("创建多项式特征...")
            df_features = self.create_polynomial_features(df_features, self.selected_features)
        
        # 保存特征名称
        if fit:
            self.feature_names = [col for col in df_features.columns 
                                if col not in ['报告时间', 'MMSI', 'IMO', '航次ID']]
        
        print(f"特征工程完成，共生成 {len(df_features.columns)} 个特征")
        return df_features

def main():
    """主函数示例"""
    # 加载数据
    df = pd.read_csv('/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/油耗数据ALL（0804）.csv')
    
    # 初始化特征工程器
    engineer = ShipFuelFeatureEngineer()
    
    # 过滤有效数据
    valid_data = df[
        (df['航行距离(nm)'] > 0) & 
        (df['重油IFO(mt)'] + df['轻油MDO/MGO(mt)'] > 0) &
        (df['平均速度(kts)'] > 0) &
        (df['航行时间(hrs)'] > 0)
    ].copy()
    
    print(f"有效数据: {len(valid_data)} 条")
    
    # 执行特征工程
    df_engineered = engineer.engineer_features(valid_data, target_col='小时油耗(mt/h)', fit=True)
    
    print("\n=== 特征工程结果 ===")
    print(f"原始特征数: {len(df.columns)}")
    print(f"工程化特征数: {len(df_engineered.columns)}")
    
    # 显示选择的特征
    if hasattr(engineer, 'selected_features'):
        print(f"\n选择的关键特征 ({len(engineer.selected_features)}):")
        for i, feature in enumerate(engineer.selected_features, 1):
            print(f"{i:2d}. {feature}")
    
    # 保存工程化数据
    output_path = '/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/engineered_features.csv'
    df_engineered.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n特征工程数据已保存至: {output_path}")

if __name__ == "__main__":
    main()
