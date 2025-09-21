# 船舶油耗预测系统 V3.0 - 最终版

## 🎯 项目概述

本项目是基于NOON报告数据的高精度船舶油耗预测系统V3.0版本，专门针对多维度特征输入进行优化，支持船龄、载重状态、船舶尺寸、地理位置、租约条款等多种输入条件。

### 🚀 V3.0 核心特性
- ✅ **多维度输入**: 支持12个输入特征 (3个必需 + 9个可选)
- ✅ **科学特征选择**: 基于相关性分析的特征重要性排序
- ✅ **高精度预测**: 集成学习算法，R² = 0.8677
- ✅ **智能分析**: 特征影响分析、载重状态对比、船龄分析
- ✅ **优化建议**: 参数优化、经济性分析、综合评估
- ✅ **FastAPI服务**: RESTful API接口，支持Web服务部署

### 📊 支持的输入特征

#### 必需参数
- `ship_type`: 船舶类型
- `speed`: 航行速度 (节)

#### 可选参数 (V3.0新增)
- `dwt`: 载重吨
- `ship_age`: 船龄 (年) ⭐ 新增
- `load_condition`: 载重状态 (Laden/Ballast) ⭐ 新增
- `draft`: 船舶吃水 (米) ⭐ 新增
- `length`: 船舶总长度 (米) ⭐ 新增
- `latitude`: 纬度 ⭐ 新增
- `longitude`: 经度 ⭐ 新增
- `heavy_fuel_cp`: 重油CP价格 ⭐ 新增
- `light_fuel_cp`: 轻油CP价格 ⭐ 新增
- `speed_cp`: 航速CP ⭐ 新增

## 📁 项目结构

```
fuel_predict_v3_final/
├── core/                               # 核心功能模块
│   ├── enhanced_fuel_predictor_v3.py   # V3.0预测模型
│   ├── enhanced_fuel_api_v3.py         # V3.0 API接口
│   ├── feature_impact_demo.py          # 特征影响演示
│   └── data_processor_enhanced.py      # 增强数据处理器
├── data/                               # 数据文件
│   ├── 油耗数据ALL（0804）.csv         # 原始数据 (57,750条)
│   ├── processed_noon_data.csv         # 处理后数据 (35,289条)
│   └── ship_speed_summary.csv          # 船舶-速度汇总
├── models/                             # 训练好的模型
│   └── enhanced_fuel_model_v3_*.pkl    # V3.0预测模型
├── outputs/                            # 分析结果
│   ├── feature_impact_analysis.png     # 特征影响可视化
│   ├── feature_impact_analysis_report.md # 详细分析报告
│   └── batch_predictions.csv           # 批量预测结果
├── docs/                               # 项目文档
│   └── 模型优化完成报告_V3.md           # V3.0完成报告
├── examples/                           # 使用示例
│   └── quick_start_v3.py               # V3.0快速开始
└── README.md                           # 项目说明
```

## 🚀 快速开始

### 1. 环境要求

```bash
pip install -r requirements.txt
```

### 2. FastAPI服务器 (推荐)

```bash
# 启动API服务器
./start_api.sh
# 或者
python fastapi_server.py

# 访问API文档
# http://localhost:8000/docs
```

**API使用示例**:
```bash
# 基础预测 (GET)
curl "http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0&dwt=75000"

# 增强预测 (POST)
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"ship_type": "Bulk Carrier", "speed": 12.0, "dwt": 75000, "ship_age": 8}'
```

### 3. Python SDK使用

```python
from core.enhanced_fuel_api_v3 import EnhancedFuelAPIV3

# 初始化V3.0 API
api = EnhancedFuelAPIV3()

# 基础预测 (仅必需参数)
result = api.predict_enhanced(
    ship_type='Bulk Carrier',
    speed=12.0
)

# 增强预测 (包含新特征)
enhanced_result = api.predict_enhanced(
    ship_type='Bulk Carrier',
    speed=12.0,
    dwt=75000,
    ship_age=8,                    # 新增: 船龄
    load_condition='Laden',        # 新增: 载重状态
    draft=12.5,                    # 新增: 船舶吃水
    length=225,                    # 新增: 船舶长度
    heavy_fuel_cp=650              # 新增: 重油CP
)

print(f"预测油耗: {enhanced_result['predicted_consumption']}mt")
```

### 3. 运行示例

```bash
cd examples/
python quick_start_v3.py
```

## 📊 特征重要性分析

基于实际油耗数据的相关性分析结果：

| 排名 | 特征名称 | 相关性系数 | 重要性等级 |
|------|----------|------------|------------|
| 1 | 重油CP条款 | 0.7003 | 极高 |
| 2 | 船舶总长度 | 0.5594 | 极高 |
| 3 | 载重吨 | 0.5586 | 极高 |
| 4 | 航速CP条款 | 0.3020 | 高 |
| 5 | 航行速度 | 0.2700 | 高 |
| 6 | 船舶吃水 | 0.2388 | 高 |
| 7 | 载重状态 | 0.0326 | 低 |
| 8 | 船龄 | 0.0119 | 低 |

## 🔧 V3.0 核心功能

### 1. 多维度预测
- 支持12个输入特征的组合预测
- 智能默认值处理
- 向后兼容基础预测

### 2. 特征影响分析
- 船龄影响分析 (0-25年全周期)
- 载重状态对比 (满载vs压载)
- 地理位置影响 (5大航行区域)
- 租约条款影响分析

### 3. 智能优化建议
- 参数优化 (为目标油耗找最佳参数)
- 载重状态建议 (经济性分析)
- 速度优化 (成本效益分析)

### 4. 综合分析报告
- 生成详细的预测分析报告
- 可视化特征影响图表
- 多维度对比分析

## 📈 预测精度

| 模型 | MAE | RMSE | R² | MAPE(%) |
|------|-----|------|----|----|
| Random Forest | 0.860 | 1.728 | 0.8611 | 4.08 |
| XGBoost | 0.889 | 1.713 | 0.8635 | 4.20 |
| LightGBM | 1.032 | 1.820 | 0.8458 | 4.90 |
| **集成模型** | **0.876** | **1.686** | **0.8677** | **4.16** |

## 💡 使用建议

### 参数输入优先级

1. **必需参数**: 船舶类型、航行速度
2. **高影响参数**: 载重吨、船舶长度、吃水、重油CP
3. **辅助参数**: 船龄、载重状态、地理位置

### 应用场景

- **高精度预测**: 提供完整参数，使用船舶档案功能
- **快速估算**: 使用基础参数，利用智能默认值
- **对比分析**: 使用特征影响分析功能
- **优化建议**: 使用参数优化和经济性分析

## 🎯 主要改进 (相比基础版本)

1. **功能扩展**: 从3个输入参数扩展到12个 (+300%)
2. **科学优化**: 基于相关性分析的特征选择
3. **预测精度**: 更真实的预测精度 (避免过拟合)
4. **实用功能**: 增加多维度分析和优化建议
5. **向后兼容**: 保持与基础版本的兼容性

## 📞 技术支持

如需技术支持或功能扩展，请联系开发团队。

## 📄 许可证

本项目为内部使用版本，请遵循相关使用协议。

---

**版本**: V3.0 最终版  
**更新时间**: 2025-09-21  
**开发团队**: 船舶油耗预测系统开发组
