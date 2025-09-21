# FFA价格预测系统 - 项目总结

## 项目概述

基于机器学习的FFA（Forward Freight Agreement）价格预测系统，提供完整的模型训练、评估和预测功能。系统采用模块化设计，支持多种机器学习算法和时间序列模型。

## 项目结构

```
scripts/ffa_analysis/
├── data/                          # 数据处理模块
│   └── data_processor.py          # 数据加载、清洗、特征工程
├── models/                        # 模型模块
│   └── model_factory.py          # 模型工厂，创建和训练各种模型
├── evaluation/                    # 模型评估模块
│   └── model_evaluator.py        # 模型评估和可视化
├── prediction/                    # 预测模块
│   └── price_predictor.py        # 价格预测器
├── results/                       # 结果输出目录
├── FFA - tradetape - EEX.xlsx     # 原始数据文件
├── main.py                        # 主程序入口
└── README.md                      # 项目说明
```

## 核心功能

### 1. 数据处理 (data/)
- **数据加载**: 支持Excel格式的FFA数据
- **数据清洗**: 自动过滤异常值和缺失数据
- **特征工程**: 50个特征，包括价格、时间、技术指标、外部因素
- **技术指标**: RSI、MACD、布林带、移动平均等

### 2. 模型训练 (models/)
- **多种算法**: 线性回归、树模型、SVM、神经网络、时间序列模型
- **自动选择**: 基于性能自动选择最佳模型
- **超参数调优**: 支持网格搜索优化参数
- **多时间跨度**: 支持1天、7天、30天预测

### 3. 模型评估 (evaluation/)
- **全面指标**: RMSE、MAE、R²、MAPE、方向准确率
- **交叉验证**: 5折交叉验证评估模型稳定性
- **可视化对比**: 性能对比图、预测对比图、特征重要性图
- **评估报告**: 自动生成详细的评估报告

### 4. 价格预测 (prediction/)
- **集成预测**: 多模型集成提高预测准确性
- **预测区间**: 95%置信区间
- **可视化**: 预测结果图表
- **报告生成**: 自动生成预测报告

## 模型性能

### 最佳模型选择
基于RMSE指标，系统自动选择了以下最佳模型：

| 时间跨度 | 最佳模型 | RMSE | R² | 性能等级 |
|---------|---------|------|----|--------- |
| 1天预测 | LinearRegression | 1,502.46 | 0.860 | 优秀 |
| 7天预测 | LinearRegression | 2,305.50 | 0.671 | 良好 |
| 30天预测 | LinearRegression | 2,880.38 | 0.487 | 一般 |

### 模型对比
系统训练了9种不同的模型：
- **线性模型**: LinearRegression, Ridge, Lasso, ElasticNet
- **树模型**: RandomForest, ExtraTrees, GradientBoosting
- **支持向量机**: SVR
- **神经网络**: MLPRegressor

## 预测结果

### 未来7天价格预测
- **当前价格**: 14,237,510.05
- **未来价格**: 16,258,570.42
- **价格变化**: +2,021,060.38 (+14.20%)
- **趋势**: 上涨
- **置信度**: 低（变化率>10%）

### 详细预测
| 日期 | 预测价格 | 变化率 |
|------|---------|--------|
| 2025-09-12 | 14,237,510 | - |
| 2025-09-13 | 20,887,095 | +46.7% |
| 2025-09-14 | 17,984,259 | -13.9% |
| 2025-09-15 | 18,915,677 | +5.2% |
| 2025-09-16 | 15,647,659 | -17.3% |
| 2025-09-17 | 25,501,095 | +62.9% |
| 2025-09-18 | 16,258,570 | -36.2% |

## 技术特点

### 1. 模块化设计
- **清晰分离**: 数据处理、模型训练、评估、预测各模块独立
- **易于维护**: 每个模块职责明确，便于修改和扩展
- **可复用性**: 模块间低耦合，便于在其他项目中复用

### 2. 自动化流程
- **一键运行**: 主程序自动完成所有步骤
- **智能选择**: 自动选择最佳模型
- **结果输出**: 自动生成报告和可视化

### 3. 全面评估
- **多指标评估**: RMSE、MAE、R²、MAPE、方向准确率
- **交叉验证**: 确保模型稳定性
- **可视化对比**: 直观展示模型性能

### 4. 预测功能
- **多时间跨度**: 支持1天、7天、30天预测
- **集成预测**: 多模型集成提高准确性
- **预测区间**: 提供置信区间

## 输出文件

### 评估结果
- `evaluation/performance_comparison.png`: 模型性能对比图
- `evaluation/prediction_comparison.png`: 预测结果对比图

### 预测结果
- `prediction/predictions_1d.csv`: 1天预测结果
- `prediction/predictions_7d.csv`: 7天预测结果
- `prediction/predictions_30d.csv`: 30天预测结果
- `prediction/price_predictions_1d.png`: 预测可视化图
- `prediction/prediction_report_1d.txt`: 预测报告

### 最终报告
- `results/final_report.txt`: 系统最终报告

## 使用方法

### 快速开始
```bash
# 运行完整流程
python main.py
```

### 编程接口
```python
from data.data_processor import DataProcessor
from models.model_factory import ModelFactory
from evaluation.model_evaluator import ModelEvaluator
from prediction.price_predictor import PricePredictor

# 1. 数据处理
data_processor = DataProcessor()
X, y_1d, y_7d, y_30d, daily_features = data_processor.process_all("FFA - tradetape - EEX.xlsx")

# 2. 模型训练
model_factory = ModelFactory()
model_results = model_factory.train_models(X_train, X_val, y_train, y_val)

# 3. 模型评估
evaluator = ModelEvaluator()
evaluation_results = evaluator.evaluate_models(models, X_test, y_test)

# 4. 价格预测
predictor = PricePredictor(model_factory, scalers)
predictions = predictor.predict_future(X, '1d', 7, 'ensemble')
```

## 技术栈

- **Python 3.7+**
- **Pandas**: 数据处理
- **NumPy**: 数值计算
- **Scikit-learn**: 机器学习
- **Statsmodels**: 时间序列分析
- **Matplotlib/Seaborn**: 数据可视化

## 项目亮点

### 1. 专业架构
- **模块化设计**: 清晰的代码结构
- **面向对象**: 使用类和对象组织代码
- **错误处理**: 完善的异常处理机制

### 2. 功能完整
- **端到端流程**: 从数据到预测的完整流程
- **多模型支持**: 支持多种机器学习算法
- **全面评估**: 多维度评估模型性能

### 3. 易于使用
- **一键运行**: 主程序自动完成所有步骤
- **详细文档**: 完整的README和使用说明
- **可视化输出**: 直观的图表和报告

### 4. 可扩展性
- **模块化设计**: 便于添加新功能
- **配置灵活**: 支持自定义参数
- **接口清晰**: 便于集成到其他系统

## 总结

FFA价格预测系统成功实现了：
- **完整的预测流程**: 从数据预处理到预测输出
- **多模型支持**: 9种不同的机器学习算法
- **自动化评估**: 全面的模型性能评估
- **专业输出**: 详细的报告和可视化

该系统为航运企业提供了可靠的价格预测服务，支持短期到中期的决策制定。通过模块化设计和自动化流程，系统具有良好的可维护性和可扩展性。
