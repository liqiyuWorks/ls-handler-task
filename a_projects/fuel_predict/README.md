# 船舶油耗预测系统 v1.0.1

基于航运行业CP条款和专业知识的智能化船舶油耗预测系统

## 🚀 快速开始

### 环境要求
```bash
pip install pandas numpy scikit-learn matplotlib seaborn xgboost lightgbm
```

### 立即使用
```bash
# 1. 简单演示 (推荐首次使用)
python simple_demo.py

# 2. 交互式菜单
python run.py

# 3. API功能测试
python prediction_api.py
```

## 📁 项目结构

```
fuel_predict/
├── 🔧 核心文件 (可直接运行)
│   ├── prediction_api.py        # 预测API (主要接口)
│   ├── model_loader.py          # 模型加载器
│   ├── simple_demo.py           # 简单演示
│   └── run.py                   # 交互式主程序
├── 📂 src/                      # 源码模块
│   ├── data_analyzer.py         # 数据分析
│   ├── cp_clause_definitions.py # CP条款定义
│   ├── feature_engineering.py   # 特征工程
│   ├── fuel_prediction_models.py# 预测模型
│   └── model_validation.py      # 模型验证
├── 📂 data/                     # 数据文件
│   └── 油耗数据ALL（0804）.csv  # 训练数据
├── 📂 models/                   # 训练好的模型
│   └── fuel_prediction_models.pkl
├── 📂 outputs/                  # 预测结果
│   ├── model_predictions.csv    # 预测结果表格
│   └── model_predictions.json   # 详细预测结果
├── 📂 reports/                  # 分析报告
├── 📂 docs/                     # 项目文档
├── 📂 examples/                 # 使用示例
└── 📂 archive/                  # 归档文件
```

## 💡 核心功能

### 1. 船舶油耗预测
```python
from prediction_api import FuelPredictionAPI

api = FuelPredictionAPI('models/fuel_prediction_models.pkl')
result = api.predict_single_voyage(ship_data)
print(f"预测油耗: {result['predicted_fuel_consumption']:.2f} mt/h")
```

### 2. 速度优化
```python
optimization = api.optimize_speed(ship_data, speed_range=(10, 16))
print(f"最优速度: {optimization['optimal_speed']} kts")
```

### 3. CP条款分析
```python
from src.cp_clause_definitions import CPClauseCalculator, ShipType, LoadCondition

calculator = CPClauseCalculator()
warranted_speed = calculator.calculate_warranted_speed(
    ShipType.BULK_CARRIER, LoadCondition.LADEN, 75000
)
```

## 🎯 支持的船型

- **散货船** (BULK CARRIER): 75,000+ 样本，R² > 0.99
- **开舱口货船** (OPEN HATCH CARGO SHIP): 6,000+ 样本
- **化学品油轮** (CHEMICAL/PRODUCTS TANKER): 2,000+ 样本
- **杂货船** (GENERAL CARGO SHIP): 1,500+ 样本
- **原油油轮** (CRUDE OIL TANKER): 600+ 样本

## 📊 系统性能

- **预测精度**: R² > 0.99, MAPE < 0.5%
- **响应时间**: 8-11ms/次
- **批量处理**: 500+ 预测/秒
- **支持船型**: 9种主要船型

## 🔧 主要文件说明

### 核心可运行文件
- **`prediction_api.py`** - 主要预测API接口
- **`simple_demo.py`** - 快速演示脚本
- **`run.py`** - 交互式主程序菜单
- **`model_loader.py`** - 模型加载工具

### 预测结果文件
- **`outputs/model_predictions.csv`** - 7个测试用例的预测结果
- **`outputs/model_predictions.json`** - 详细预测结果和分析

## 🎉 使用示例

### 预测结果示例
| 船型 | 载重吨 | 速度 | 预测油耗 |
|------|--------|------|----------|
| 散货船 | 75,000 | 12.5kts | 22.15 mt/h |
| 开舱口货船 | 62,000 | 13.0kts | 28.84 mt/h |
| 化学品油轮 | 45,000 | 11.8kts | 12.59 mt/h |

### CP条款分析示例
- 保证航速: 11.5 kts
- 保证日油耗: 29.9 mt/day
- 性能指数: 77.5

## 📞 技术支持

- 查看 `outputs/` 目录获取预测结果
- 查看 `reports/` 目录获取分析报告
- 运行 `python run.py` 获取交互式帮助

---

**系统状态**: ✅ 稳定运行  
**版本**: v1.0.1  
**最后更新**: 2025-09-18
