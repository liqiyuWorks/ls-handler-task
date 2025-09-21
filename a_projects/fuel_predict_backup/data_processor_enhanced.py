#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版数据处理器 - 专门处理NOON报告数据
Enhanced Data Processor for NOON Report Analysis

功能：
1. 筛选NOON报告类型且航行时间为24或25小时的数据
2. 基于航运行业属性和租约条款进行特征工程
3. 船舶档案特征提取和处理
4. 数据质量控制和异常值处理

作者: 船舶油耗预测系统
日期: 2025-09-21
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class EnhancedDataProcessor:
    """增强版数据处理器"""
    
    def __init__(self):
        self.ship_type_mapping = {
            'BULK CARRIER': 'Bulk Carrier',
            'Bulk Carrier': 'Bulk Carrier',
            'OPEN HATCH CARGO SHIP': 'Open Hatch Cargo',
            'CHEMICAL/PRODUCTS TANKER': 'Chemical Tanker',
            'Chemical/Products Tanker': 'Chemical Tanker',
            'GENERAL CARGO SHIP': 'General Cargo',
            'General Cargo Ship': 'General Cargo',
            'GENERAL CARGO SHIP (OPEN HATCH)': 'General Cargo',
            'CRUDE OIL TANKER': 'Crude Oil Tanker',
            'Crude Oil Tanker': 'Crude Oil Tanker',
            'PRODUCTS TANKER': 'Chemical Tanker',
            'CONTAINER SHIP': 'Container Ship',
            'Container Ship': 'Container Ship',
            'BULK/CAUSTIC SODA CARRIER (CABU)': 'Bulk Carrier',
            'HEAVY LOAD CARRIER': 'General Cargo',
            'OTHER': 'Other',
            'other': 'Other',
            'tanker': 'Chemical Tanker'
        }
        
        # 船舶类型系数 (基于航运行业经验)
        self.ship_efficiency_factors = {
            'Bulk Carrier': 1.0,
            'Container Ship': 1.15,
            'Crude Oil Tanker': 0.95,
            'Chemical Tanker': 1.05,
            'General Cargo': 1.10,
            'Open Hatch Cargo': 1.08,
            'Other': 1.12
        }
        
        # 载重状态系数
        self.load_condition_factors = {
            'Laden': 1.0,
            'Ballast': 0.85,
            'None': 0.95
        }
    
    def load_and_filter_data(self, data_path: str) -> pd.DataFrame:
        """
        加载并筛选数据
        只保留NOON报告且航行时间为24或25小时的数据
        """
        print("📊 正在加载和筛选数据...")
        
        # 读取数据
        df = pd.read_csv(data_path)
        print(f"原始数据行数: {len(df)}")
        
        # 筛选NOON报告
        noon_data = df[df['报告类型'] == 'NOON'].copy()
        print(f"NOON报告数据行数: {len(noon_data)}")
        
        # 筛选24或25小时航行数据
        filtered_data = noon_data[
            (noon_data['航行时间(hrs)'] == 24) | 
            (noon_data['航行时间(hrs)'] == 25)
        ].copy()
        print(f"筛选后数据行数: {len(filtered_data)}")
        
        # 数据质量检查
        self._quality_check(filtered_data)
        
        return filtered_data
    
    def _quality_check(self, df: pd.DataFrame):
        """数据质量检查"""
        print("\n🔍 数据质量检查:")
        
        key_columns = ['重油IFO(mt)', '平均速度(kts)', '船舶载重(t)', '船舶类型']
        for col in key_columns:
            missing = df[col].isna().sum()
            print(f"  {col}: {missing} 个缺失值")
        
        # 检查异常值
        fuel_outliers = df[df['重油IFO(mt)'] > 100].shape[0]
        speed_outliers = df[df['平均速度(kts)'] > 25].shape[0]
        print(f"  重油消耗异常值 (>100mt): {fuel_outliers}")
        print(f"  速度异常值 (>25kts): {speed_outliers}")
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特征工程 - 基于航运行业属性和租约条款
        """
        print("\n⚙️ 进行特征工程...")
        
        enhanced_df = df.copy()
        
        # 1. 船舶类型标准化
        enhanced_df['船舶类型_标准化'] = enhanced_df['船舶类型'].map(
            self.ship_type_mapping
        ).fillna('Other')
        
        # 2. 船舶效率系数 (基于船型)
        enhanced_df['船舶效率系数'] = enhanced_df['船舶类型_标准化'].map(
            self.ship_efficiency_factors
        )
        
        # 3. 载重状态系数
        enhanced_df['载重状态_填充'] = enhanced_df['载重状态'].fillna('None')
        enhanced_df['载重状态系数'] = enhanced_df['载重状态_填充'].map(
            self.load_condition_factors
        )
        
        # 4. 船舶尺寸特征
        enhanced_df['载重吨位等级'] = pd.cut(
            enhanced_df['船舶载重(t)'], 
            bins=[0, 20000, 50000, 100000, 200000, float('inf')],
            labels=['小型', '中型', '大型', '超大型', '巨型']
        )
        
        # 5. 船龄分组
        enhanced_df['船龄_数值'] = pd.to_numeric(enhanced_df['船龄'], errors='coerce')
        enhanced_df['船龄分组'] = pd.cut(
            enhanced_df['船龄_数值'],
            bins=[0, 5, 10, 20, float('inf')],
            labels=['新船', '中等船龄', '老船', '高龄船']
        )
        
        # 6. 速度效率指标
        enhanced_df['速度效率'] = enhanced_df['航行距离(nm)'] / enhanced_df['航行时间(hrs)']
        enhanced_df['理论速度差异'] = enhanced_df['平均速度(kts)'] - enhanced_df['速度效率']
        
        # 7. 租约条款相关特征 (基于CP条款)
        enhanced_df['重油CP_标准化'] = enhanced_df['重油cp'].fillna(enhanced_df['重油cp'].median())
        enhanced_df['轻油CP_标准化'] = enhanced_df['轻油cp'].fillna(enhanced_df['轻油cp'].median())
        enhanced_df['航速CP_标准化'] = enhanced_df['航速cp'].fillna(enhanced_df['航速cp'].median())
        
        # 8. 油耗效率指标 (防止除零错误)
        enhanced_df['单位距离油耗'] = enhanced_df['重油IFO(mt)'] / np.maximum(enhanced_df['航行距离(nm)'], 0.1)
        enhanced_df['单位时间油耗'] = enhanced_df['重油IFO(mt)'] / np.maximum(enhanced_df['航行时间(hrs)'], 0.1)
        enhanced_df['载重吨油耗比'] = enhanced_df['重油IFO(mt)'] / np.maximum(enhanced_df['船舶载重(t)'], 1000) * 1000
        
        # 9. 综合效率指标
        enhanced_df['综合效率指标'] = (
            enhanced_df['船舶效率系数'] * 
            enhanced_df['载重状态系数'] * 
            enhanced_df['平均速度(kts)'] / 10
        )
        
        # 10. 地理位置特征 (从位置字符串提取)
        enhanced_df = self._extract_location_features(enhanced_df)
        
        print(f"特征工程完成，新增特征数: {len(enhanced_df.columns) - len(df.columns)}")
        
        return enhanced_df
    
    def _extract_location_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取地理位置特征"""
        try:
            # 解析位置坐标
            location_data = df['位置'].str.extract(r'\(([^,]+),\s*([^)]+)\)')
            df['纬度'] = pd.to_numeric(location_data[0], errors='coerce')
            df['经度'] = pd.to_numeric(location_data[1], errors='coerce')
            
            # 地理区域分类
            df['航行区域'] = 'Unknown'
            
            # 根据经纬度划分主要航运区域
            conditions = [
                (df['纬度'].between(-10, 30) & df['经度'].between(30, 120)),  # 印度洋
                (df['纬度'].between(0, 50) & df['经度'].between(100, 180)),    # 西太平洋
                (df['纬度'].between(30, 70) & df['经度'].between(-30, 50)),    # 北大西洋
                (df['纬度'].between(-40, 0) & df['经度'].between(-70, 20)),    # 南大西洋
                (df['纬度'].between(10, 50) & df['经度'].between(80, 140)),    # 东亚海域
            ]
            
            choices = ['印度洋', '西太平洋', '北大西洋', '南大西洋', '东亚海域']
            
            df['航行区域'] = np.select(conditions, choices, default='其他区域')
            
        except Exception as e:
            print(f"位置特征提取出错: {e}")
            df['纬度'] = 0
            df['经度'] = 0
            df['航行区域'] = 'Unknown'
        
        return df
    
    def prepare_model_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        准备用于模型训练的数据
        """
        print("\n📋 准备模型训练数据...")
        
        # 选择特征列
        feature_columns = [
            # 基础特征
            '平均速度(kts)', '航行距离(nm)', '航行时间(hrs)',
            '船舶载重(t)', '船舶吃水(m)', '船舶总长度(m)',
            
            # 工程化特征
            '船舶效率系数', '载重状态系数',
            '单位距离油耗', '单位时间油耗', '载重吨油耗比',
            '综合效率指标', '理论速度差异',
            
            # 租约特征
            '重油CP_标准化', '轻油CP_标准化', '航速CP_标准化',
            
            # 位置特征
            '纬度', '经度'
        ]
        
        # 分类特征编码
        categorical_features = ['船舶类型_标准化', '载重吨位等级', '船龄分组', '载重状态_填充', '航行区域']
        
        model_df = df.copy()
        
        # 对分类特征进行编码
        for cat_feature in categorical_features:
            if cat_feature in model_df.columns:
                model_df[f'{cat_feature}_编码'] = pd.Categorical(model_df[cat_feature]).codes
                feature_columns.append(f'{cat_feature}_编码')
        
        # 处理缺失值
        for col in feature_columns:
            if col in model_df.columns:
                if model_df[col].dtype in ['float64', 'int64']:
                    model_df[col] = model_df[col].fillna(model_df[col].median())
                else:
                    model_df[col] = model_df[col].fillna(0)
        
        # 异常值处理
        model_df = self._handle_outliers(model_df)
        
        print(f"模型特征数量: {len(feature_columns)}")
        print(f"训练数据行数: {len(model_df)}")
        
        return model_df, feature_columns
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值"""
        # 使用IQR方法处理重油消耗异常值
        Q1 = df['重油IFO(mt)'].quantile(0.25)
        Q3 = df['重油IFO(mt)'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # 限制异常值
        df.loc[df['重油IFO(mt)'] < lower_bound, '重油IFO(mt)'] = lower_bound
        df.loc[df['重油IFO(mt)'] > upper_bound, '重油IFO(mt)'] = upper_bound
        
        return df
    
    def get_ship_speed_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成船舶-速度-油耗汇总表
        用于"XX船舶在XX平均速度下的重油mt预测"
        """
        print("\n📈 生成船舶-速度-油耗汇总...")
        
        summary = df.groupby(['船舶类型_标准化', '平均速度(kts)']).agg({
            '重油IFO(mt)': ['mean', 'std', 'count'],
            '船舶载重(t)': 'mean',
            '载重状态系数': 'mean',
            '综合效率指标': 'mean'
        }).round(2)
        
        # 扁平化列名
        summary.columns = [f'{col[0]}_{col[1]}' if col[1] else col[0] for col in summary.columns]
        summary = summary.reset_index()
        
        # 只保留有足够样本的组合
        summary = summary[summary['重油IFO(mt)_count'] >= 5]
        
        print(f"船舶-速度组合数: {len(summary)}")
        
        return summary

def main():
    """主函数 - 演示数据处理流程"""
    processor = EnhancedDataProcessor()
    
    # 数据路径
    data_path = "data/油耗数据ALL（0804）.csv"
    
    try:
        # 1. 加载和筛选数据
        filtered_data = processor.load_and_filter_data(data_path)
        
        # 2. 特征工程
        enhanced_data = processor.engineer_features(filtered_data)
        
        # 3. 准备模型数据
        model_data, feature_columns = processor.prepare_model_data(enhanced_data)
        
        # 4. 生成汇总表
        summary = processor.get_ship_speed_summary(enhanced_data)
        
        # 5. 保存处理后的数据
        output_path = "data/processed_noon_data.csv"
        model_data.to_csv(output_path, index=False)
        print(f"\n✅ 处理完成！数据已保存到: {output_path}")
        
        # 保存汇总表
        summary_path = "data/ship_speed_summary.csv"
        summary.to_csv(summary_path, index=False)
        print(f"✅ 汇总表已保存到: {summary_path}")
        
        # 显示统计信息
        print(f"\n📊 最终数据统计:")
        print(f"  - 总行数: {len(model_data)}")
        print(f"  - 特征数: {len(feature_columns)}")
        print(f"  - 船舶类型: {enhanced_data['船舶类型_标准化'].nunique()}")
        print(f"  - 速度范围: {model_data['平均速度(kts)'].min():.1f} - {model_data['平均速度(kts)'].max():.1f} kts")
        print(f"  - 油耗范围: {model_data['重油IFO(mt)'].min():.1f} - {model_data['重油IFO(mt)'].max():.1f} mt")
        
        return model_data, feature_columns, summary
        
    except Exception as e:
        print(f"❌ 数据处理出错: {e}")
        return None, None, None

if __name__ == "__main__":
    main()
