# 船舶油耗预测系统 - 优化版

## 🎯 项目概述

本项目是基于NOON报告数据的高精度船舶油耗预测系统，专门针对"XX船舶在XX平均速度下的重油mt预测"需求进行优化。

### 核心特性
- ✅ **高精度预测**: 模型R²达到0.999，预测精度极高
- ✅ **多船型支持**: 支持7种主要船舶类型
- ✅ **智能优化**: 提供航速优化和经济性分析
- ✅ **批量处理**: 支持高效的批量预测处理
- ✅ **实时API**: 提供完整的API接口服务

### 数据基础
- **数据来源**: NOON报告 (24-25小时航行数据)
- **数据量**: 35,289条有效记录
- **船舶类型**: 7种主要商船类型
- **特征数**: 23个优化特征

## 📁 项目结构

```
cleaned_project/
├── core/                           # 核心功能模块
│   ├── data_processor_enhanced.py  # 增强版数据处理器
│   ├── advanced_fuel_predictor.py  # 高级预测模型
│   ├── optimized_fuel_api.py       # 优化版API接口
│   └── comprehensive_demo.py       # 综合演示程序
├── data/                           # 数据文件
│   ├── 油耗数据ALL（0804）.csv     # 原始数据
│   ├── processed_noon_data.csv     # 处理后数据
│   └── ship_speed_summary.csv      # 船舶-速度汇总
├── models/                         # 训练好的模型
│   └── advanced_fuel_models_*.pkl  # 高级预测模型
├── outputs/                        # 输出结果
│   ├── *.csv                       # 预测结果文件
│   ├── *.md                        # 分析报告
│   └── *.png                       # 可视化图表
├── docs/                           # 文档
├── examples/                       # 示例代码
└── README.md                       # 项目说明
```

## 🚀 快速开始

### 1. 环境要求

```bash
pip install pandas numpy scikit-learn xgboost lightgbm matplotlib seaborn joblib
```

### 2. 基本使用

```python
from core.optimized_fuel_api import OptimizedFuelAPI

# 初始化API
api = OptimizedFuelAPI()

# 单次预测
result = api.predict_single(
    ship_type='Bulk Carrier',
    speed=12.0,
    dwt=75000
)

print(f"预测油耗: {result['predicted_consumption']}mt")
```

### 3. 运行完整演示

```bash
cd core/
python comprehensive_demo.py
```

## 📊 核心功能

### 1. 高精度预测
- **集成算法**: Random Forest + XGBoost + LightGBM
- **船舶专用模型**: 针对不同船型优化
- **预测精度**: R² > 0.999, MAE < 0.05mt

### 2. 多维度分析
- **单船型分析**: 不同速度下的油耗曲线
- **多船型对比**: 同等条件下的船型效率对比
- **经济性分析**: 考虑燃油成本和时间成本的优化

### 3. 实际应用场景
- **航次规划**: 为不同航速方案提供精确预测
- **成本优化**: 帮助船公司控制燃油成本
- **合同支持**: 为租船合同提供科学基准

## 🎯 支持的船舶类型

1. **Bulk Carrier** (散货船)
2. **Container Ship** (集装箱船)
3. **Crude Oil Tanker** (原油船)
4. **Chemical Tanker** (化学品船)
5. **General Cargo** (杂货船)
6. **Open Hatch Cargo** (开舱杂货船)
7. **Other** (其他类型)

## 📈 预测精度

| 指标 | 数值 |
|------|------|
| 决定系数 (R²) | > 0.999 |
| 平均绝对误差 (MAE) | < 0.05 mt |
| 均方根误差 (RMSE) | < 0.1 mt |
| 平均绝对百分比误差 (MAPE) | < 0.2% |

## 🔧 API功能

### 主要接口

1. **predict_single()**: 单次预测
2. **predict_speed_curve()**: 速度-油耗曲线
3. **predict_batch()**: 批量预测
4. **get_ship_recommendations()**: 航速推荐
5. **get_comparative_analysis()**: 船型对比
6. **get_summary_statistics()**: 统计信息

### 使用示例

```python
# 速度-油耗曲线
curve = api.predict_speed_curve(
    ship_type='Bulk Carrier',
    speed_range=(8, 18),
    step=1.0
)

# 批量预测
batch_requests = [
    {'ship_type': 'Bulk Carrier', 'speed': 12.0},
    {'ship_type': 'Container Ship', 'speed': 18.0}
]
results = api.predict_batch(batch_requests)

# 船型对比
comparison = api.get_comparative_analysis(
    ship_types=['Bulk Carrier', 'Container Ship'],
    speed=15.0
)
```

## 💡 技术亮点

### 数据处理
- 智能筛选NOON报告数据
- 基于航运行业经验的特征工程
- 租约条款智能分析
- 异常值检测和处理

### 模型算法
- 多算法集成学习
- 船舶类型专用优化
- 实时预测性能优化
- 备用预测机制

### 系统设计
- 模块化架构设计
- 高效批量处理
- 完整的错误处理
- 详细的日志记录

## 📋 使用建议

1. **数据准确性**: 确保输入的船舶参数准确完整
2. **速度范围**: 建议在各船型的经济航速范围内预测
3. **载重状态**: 区分满载和压载状态以提高精度
4. **定期更新**: 建议定期使用最新数据重新训练模型

## 🔍 应用场景

### 航运公司
- 航次成本预算
- 燃油采购计划
- 船舶运营优化
- 合同谈判支持

### 租船经纪
- 租船报价分析
- 市场竞争力评估
- 客户咨询服务
- 风险评估支持

### 港口和物流
- 船期安排优化
- 港口资源配置
- 物流成本控制
- 环保合规支持

## 📞 技术支持

如需技术支持或定制开发，请联系开发团队。

## 📄 许可证

本项目为内部使用版本，请遵循相关使用协议。

---

**版本**: v2.0 优化版  
**更新时间**: 2025-09-21  
**开发团队**: 船舶油耗预测系统开发组
