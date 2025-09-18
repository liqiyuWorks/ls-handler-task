#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗数据分析模块
基于航运行业标准和CP条款的数据分析工具

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ShipFuelDataAnalyzer:
    """船舶油耗数据分析器"""
    
    def __init__(self, data_path: str):
        """
        初始化数据分析器
        
        Args:
            data_path: 数据文件路径
        """
        self.data_path = data_path
        self.df = None
        self.ship_types = None
        self.load_status_types = None
        
    def load_data(self) -> pd.DataFrame:
        """加载油耗数据"""
        print("正在加载油耗数据...")
        self.df = pd.read_csv(self.data_path, encoding='utf-8')
        
        # 数据预处理
        self.df['报告时间'] = pd.to_datetime(self.df['报告时间'], unit='ms')
        
        # 计算单位油耗指标
        self.df['重油单耗_mt_per_nm'] = np.where(
            self.df['航行距离(nm)'] > 0,
            self.df['重油IFO(mt)'] / self.df['航行距离(nm)'],
            0
        )
        
        self.df['轻油单耗_mt_per_nm'] = np.where(
            self.df['航行距离(nm)'] > 0,
            self.df['轻油MDO/MGO(mt)'] / self.df['航行距离(nm)'],
            0
        )
        
        # 总油耗
        self.df['总油耗(mt)'] = self.df['重油IFO(mt)'] + self.df['轻油MDO/MGO(mt)']
        
        # 单位时间油耗
        self.df['小时油耗(mt/h)'] = np.where(
            self.df['航行时间(hrs)'] > 0,
            self.df['总油耗(mt)'] / self.df['航行时间(hrs)'],
            0
        )
        
        # 载重比
        self.df['载重比'] = self.df['船舶吃水(m)'] / self.df['船舶载重(t)'] * 10000
        
        print(f"数据加载完成，共 {len(self.df)} 条记录")
        return self.df
    
    def get_basic_statistics(self) -> Dict:
        """获取基础统计信息"""
        if self.df is None:
            self.load_data()
            
        stats = {
            '数据总量': len(self.df),
            '船舶数量': self.df['MMSI'].nunique(),
            '船型分布': self.df['船舶类型'].value_counts().to_dict(),
            '载重状态分布': self.df['载重状态'].value_counts().to_dict(),
            '报告类型分布': self.df['报告类型'].value_counts().to_dict(),
            '时间范围': {
                '开始时间': self.df['报告时间'].min(),
                '结束时间': self.df['报告时间'].max()
            }
        }
        
        return stats
    
    def analyze_ship_types(self) -> pd.DataFrame:
        """分析不同船型的特征"""
        if self.df is None:
            self.load_data()
            
        # 过滤有效航行数据
        valid_data = self.df[
            (self.df['航行距离(nm)'] > 0) & 
            (self.df['总油耗(mt)'] > 0) &
            (self.df['平均速度(kts)'] > 0)
        ]
        
        ship_analysis = valid_data.groupby('船舶类型').agg({
            'MMSI': 'nunique',
            '船舶载重(t)': ['mean', 'std', 'min', 'max'],
            '船舶总长度(m)': ['mean', 'std', 'min', 'max'],
            '平均速度(kts)': ['mean', 'std', 'min', 'max'],
            '重油IFO(mt)': ['mean', 'sum'],
            '轻油MDO/MGO(mt)': ['mean', 'sum'],
            '总油耗(mt)': ['mean', 'sum'],
            '小时油耗(mt/h)': ['mean', 'std'],
            '重油单耗_mt_per_nm': ['mean', 'std'],
            '航行距离(nm)': ['mean', 'sum'],
            '重油cp': 'mean',
            '轻油cp': 'mean',
            '航速cp': 'mean'
        }).round(3)
        
        ship_analysis.columns = ['_'.join(col).strip() for col in ship_analysis.columns]
        
        return ship_analysis
    
    def analyze_speed_fuel_relationship(self) -> Dict:
        """分析速度与油耗的关系"""
        if self.df is None:
            self.load_data()
            
        # 过滤有效数据
        valid_data = self.df[
            (self.df['航行距离(nm)'] > 0) & 
            (self.df['总油耗(mt)'] > 0) &
            (self.df['平均速度(kts)'] > 0) &
            (self.df['平均速度(kts)'] < 25)  # 排除异常速度
        ]
        
        correlation_analysis = {}
        
        for ship_type in valid_data['船舶类型'].unique():
            ship_data = valid_data[valid_data['船舶类型'] == ship_type]
            if len(ship_data) > 10:  # 确保有足够的数据点
                corr_speed_fuel = ship_data['平均速度(kts)'].corr(ship_data['小时油耗(mt/h)'])
                corr_speed_consumption = ship_data['平均速度(kts)'].corr(ship_data['重油单耗_mt_per_nm'])
                
                correlation_analysis[ship_type] = {
                    '样本数': len(ship_data),
                    '速度-小时油耗相关性': round(corr_speed_fuel, 3),
                    '速度-单位距离油耗相关性': round(corr_speed_consumption, 3),
                    '平均速度': round(ship_data['平均速度(kts)'].mean(), 2),
                    '平均小时油耗': round(ship_data['小时油耗(mt/h)'].mean(), 3)
                }
        
        return correlation_analysis
    
    def analyze_load_status_impact(self) -> pd.DataFrame:
        """分析载重状态对油耗的影响"""
        if self.df is None:
            self.load_data()
            
        valid_data = self.df[
            (self.df['航行距离(nm)'] > 0) & 
            (self.df['总油耗(mt)'] > 0) &
            (self.df['载重状态'].notna())
        ]
        
        load_analysis = valid_data.groupby(['船舶类型', '载重状态']).agg({
            'MMSI': 'nunique',
            '平均速度(kts)': 'mean',
            '小时油耗(mt/h)': ['mean', 'std'],
            '重油单耗_mt_per_nm': ['mean', 'std'],
            '船舶吃水(m)': 'mean',
            '载重比': 'mean'
        }).round(3)
        
        return load_analysis
    
    def create_visualization_dashboard(self, save_path: str = None):
        """创建可视化仪表板"""
        if self.df is None:
            self.load_data()
            
        # 创建图表
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('船舶油耗数据分析仪表板', fontsize=16, fontweight='bold')
        
        # 过滤有效数据
        valid_data = self.df[
            (self.df['航行距离(nm)'] > 0) & 
            (self.df['总油耗(mt)'] > 0) &
            (self.df['平均速度(kts)'] > 0) &
            (self.df['平均速度(kts)'] < 25)
        ]
        
        # 1. 船型分布
        ship_counts = valid_data['船舶类型'].value_counts()
        axes[0,0].pie(ship_counts.values, labels=ship_counts.index, autopct='%1.1f%%')
        axes[0,0].set_title('船型分布')
        
        # 2. 速度vs油耗散点图
        for ship_type in valid_data['船舶类型'].unique()[:5]:  # 显示前5种船型
            ship_data = valid_data[valid_data['船舶类型'] == ship_type]
            axes[0,1].scatter(ship_data['平均速度(kts)'], ship_data['小时油耗(mt/h)'], 
                            label=ship_type, alpha=0.6)
        axes[0,1].set_xlabel('平均速度 (kts)')
        axes[0,1].set_ylabel('小时油耗 (mt/h)')
        axes[0,1].set_title('速度与油耗关系')
        axes[0,1].legend()
        
        # 3. 载重状态对比
        load_fuel = valid_data.groupby('载重状态')['小时油耗(mt/h)'].mean()
        axes[0,2].bar(load_fuel.index, load_fuel.values)
        axes[0,2].set_title('载重状态vs平均油耗')
        axes[0,2].set_ylabel('平均小时油耗 (mt/h)')
        
        # 4. 船舶载重分布
        axes[1,0].hist(valid_data['船舶载重(t)'], bins=30, alpha=0.7)
        axes[1,0].set_xlabel('船舶载重 (t)')
        axes[1,0].set_ylabel('频次')
        axes[1,0].set_title('船舶载重分布')
        
        # 5. CP条款速度对比
        cp_speed_data = valid_data[valid_data['航速cp'] > 0]
        axes[1,1].scatter(cp_speed_data['航速cp'], cp_speed_data['平均速度(kts)'], alpha=0.6)
        axes[1,1].plot([0, 25], [0, 25], 'r--', label='理想线')
        axes[1,1].set_xlabel('CP条款航速 (kts)')
        axes[1,1].set_ylabel('实际平均速度 (kts)')
        axes[1,1].set_title('CP条款航速 vs 实际航速')
        axes[1,1].legend()
        
        # 6. 油耗效率分析
        ship_efficiency = valid_data.groupby('船舶类型')['重油单耗_mt_per_nm'].mean().sort_values()
        axes[1,2].barh(range(len(ship_efficiency)), ship_efficiency.values)
        axes[1,2].set_yticks(range(len(ship_efficiency)))
        axes[1,2].set_yticklabels(ship_efficiency.index)
        axes[1,2].set_xlabel('单位距离重油消耗 (mt/nm)')
        axes[1,2].set_title('各船型油耗效率对比')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")
        
        return fig
    
    def generate_analysis_report(self) -> str:
        """生成分析报告"""
        if self.df is None:
            self.load_data()
            
        basic_stats = self.get_basic_statistics()
        ship_analysis = self.analyze_ship_types()
        speed_fuel_corr = self.analyze_speed_fuel_relationship()
        
        report = f"""
# 船舶油耗数据分析报告

## 1. 数据概览
- 总记录数: {basic_stats['数据总量']:,} 条
- 船舶数量: {basic_stats['船舶数量']} 艘
- 数据时间范围: {basic_stats['时间范围']['开始时间'].strftime('%Y-%m-%d')} 至 {basic_stats['时间范围']['结束时间'].strftime('%Y-%m-%d')}

## 2. 船型分布
"""
        
        for ship_type, count in basic_stats['船型分布'].items():
            report += f"- {ship_type}: {count} 条记录\n"
        
        report += "\n## 3. 载重状态分布\n"
        for status, count in basic_stats['载重状态分布'].items():
            report += f"- {status}: {count} 条记录\n"
        
        report += "\n## 4. 速度与油耗相关性分析\n"
        for ship_type, corr_data in speed_fuel_corr.items():
            report += f"\n### {ship_type}\n"
            report += f"- 样本数: {corr_data['样本数']}\n"
            report += f"- 速度与小时油耗相关性: {corr_data['速度-小时油耗相关性']}\n"
            report += f"- 平均速度: {corr_data['平均速度']} kts\n"
            report += f"- 平均小时油耗: {corr_data['平均小时油耗']} mt/h\n"
        
        report += "\n## 5. 关键发现和建议\n"
        report += "- 不同船型的油耗特征存在显著差异，需要建立分船型的预测模型\n"
        report += "- 速度与油耗呈现非线性关系，建议在模型中考虑速度的二次项或三次项\n"
        report += "- 载重状态对油耗有重要影响，满载状态下油耗通常更高\n"
        report += "- CP条款中的航速与实际航速存在差异，需要在预测中考虑这种偏差\n"
        
        return report

def main():
    """主函数示例"""
    # 初始化分析器
    analyzer = ShipFuelDataAnalyzer('/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/油耗数据ALL（0804）.csv')
    
    # 加载数据
    df = analyzer.load_data()
    
    # 基础统计
    print("=== 基础统计信息 ===")
    stats = analyzer.get_basic_statistics()
    for key, value in stats.items():
        if key != '时间范围':
            print(f"{key}: {value}")
    
    # 船型分析
    print("\n=== 船型特征分析 ===")
    ship_analysis = analyzer.analyze_ship_types()
    print(ship_analysis)
    
    # 速度油耗关系
    print("\n=== 速度与油耗相关性 ===")
    corr_analysis = analyzer.analyze_speed_fuel_relationship()
    for ship_type, data in corr_analysis.items():
        print(f"{ship_type}: {data}")
    
    # 生成可视化
    print("\n=== 生成可视化图表 ===")
    fig = analyzer.create_visualization_dashboard('/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/analysis_dashboard.png')
    
    # 生成报告
    print("\n=== 生成分析报告 ===")
    report = analyzer.generate_analysis_report()
    with open('/home/lisheng/liqiyuWorks/ls-handler-task/a_projects/fuel_predict/analysis_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("分析完成！")

if __name__ == "__main__":
    main()
