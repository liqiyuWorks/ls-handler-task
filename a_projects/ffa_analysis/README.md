# FFA价格预测系统

基于机器学习的FFA（Forward Freight Agreement）价格预测系统，提供完整的模型训练、评估和预测功能。

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

## 功能特点

### 1. 数据处理
- **数据加载**: 支持Excel格式的FFA数据
- **数据清洗**: 自动过滤异常值和缺失数据
- **特征工程**: 50+个特征，包括价格、时间、技术指标、外部因素
- **技术指标**: RSI、MACD、布林带、移动平均等

### 2. 模型训练
- **多种算法**: 线性回归、树模型、SVM、神经网络、时间序列模型
- **自动选择**: 基于性能自动选择最佳模型
- **超参数调优**: 支持网格搜索优化参数
- **多时间跨度**: 支持1天、7天、30天预测

### 3. 模型评估
- **全面指标**: RMSE、MAE、R²、MAPE、方向准确率
- **交叉验证**: 5折交叉验证评估模型稳定性
- **可视化对比**: 性能对比图、预测对比图、特征重要性图
- **评估报告**: 自动生成详细的评估报告

### 4. 价格预测
- **集成预测**: 多模型集成提高预测准确性
- **预测区间**: 95%置信区间
- **可视化**: 预测结果图表
- **报告生成**: 自动生成预测报告

## 支持的模型

### 机器学习模型
- **线性模型**: LinearRegression, Ridge, Lasso, ElasticNet
- **树模型**: RandomForest, ExtraTrees, GradientBoosting
- **支持向量机**: SVR
- **神经网络**: MLPRegressor
- **梯度提升**: XGBoost, LightGBM

### 时间序列模型
- **ARIMA**: 自回归积分滑动平均模型
- **SARIMAX**: 季节性ARIMA模型

## 快速开始

### 1. 安装依赖

```bash
pip install pandas numpy scikit-learn matplotlib seaborn openpyxl xgboost lightgbm statsmodels
```

### 2. 运行完整流程

```bash
python main.py
```

### 3. 查看结果

运行完成后，结果将保存在以下目录：
- `evaluation/`: 模型评估图表和报告
- `prediction/`: 预测结果和可视化
- `results/`: 最终报告

## 使用方法

### 基本使用

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

### 自定义模型训练

```python
# 创建特定模型
model_factory = ModelFactory()
models = model_factory.create_models()

# 训练特定模型
results = model_factory.train_models(X_train, X_val, y_train, y_val, 
                                   model_names=['Ridge', 'RandomForest', 'XGBoost'])

# 超参数调优
param_grid = {'alpha': [0.1, 1.0, 10.0]}
best_model = model_factory.hyperparameter_tuning(X_train, X_val, y_train, y_val, 
                                                'Ridge', param_grid)
```

### 模型评估

```python
# 创建评估器
evaluator = ModelEvaluator()

# 评估模型
results = evaluator.evaluate_models(models, X_test, y_test)

# 创建可视化
evaluator.create_performance_comparison('evaluation/performance.png')
evaluator.create_prediction_comparison(y_test, predictions, 'evaluation/comparison.png')
evaluator.create_feature_importance_plot(feature_importance, 'evaluation/importance.png')

# 生成报告
evaluator.generate_evaluation_report('evaluation/report.txt')
```

### 价格预测

```python
# 创建预测器
predictor = PricePredictor(model_factory, scalers)

# 单模型预测
predictions = predictor.predict_single(X, 'Ridge', '1d')

# 集成预测
ensemble_pred, individual_preds = predictor.predict_ensemble(X, '1d')

# 未来预测
future_predictions = predictor.predict_future(X, '1d', 7, 'ensemble')

# 创建可视化
predictor.create_prediction_visualization(future_predictions, historical_data)

# 生成报告
predictor.generate_prediction_report(future_predictions)
```

## 特征说明

### 价格特征
- `Price_Mean`: 日平均价格
- `Price_Std`: 价格标准差
- `Price_MA_7`: 7日移动平均
- `Price_Change_1d`: 1日价格变化率
- `Price_Volatility_7d`: 7日价格波动率

### 技术指标
- `RSI_14`: 14日相对强弱指数
- `MACD`: 移动平均收敛发散
- `Bollinger_Upper/Lower`: 布林带上下轨

### 时间特征
- `Year`, `Month`, `Day`: 年月日
- `DayOfWeek`: 星期几
- `IsWeekend`: 是否周末
- `Quarter`: 季度

### 外部特征
- `Oil_Price`: 原油价格
- `Iron_Ore_Price`: 铁矿石价格
- `Coal_Price`: 煤炭价格
- `GDP_Growth`: GDP增长率
- `Trade_Volume_Index`: 贸易量指数
- `PMI`: 采购经理人指数

## 输出文件

### 评估结果
- `evaluation/performance_comparison.png`: 模型性能对比图
- `evaluation/prediction_comparison.png`: 预测结果对比图
- `evaluation/feature_importance.png`: 特征重要性图
- `evaluation/evaluation_report.txt`: 评估报告

### 预测结果
- `prediction/predictions_1d.csv`: 1天预测结果
- `prediction/predictions_7d.csv`: 7天预测结果
- `prediction/predictions_30d.csv`: 30天预测结果
- `prediction/price_predictions_1d.png`: 预测可视化图
- `prediction/prediction_report_1d.txt`: 预测报告

### 最终报告
- `results/final_report.txt`: 系统最终报告

## 技术栈

- **Python 3.7+**
- **Pandas**: 数据处理
- **NumPy**: 数值计算
- **Scikit-learn**: 机器学习
- **XGBoost/LightGBM**: 梯度提升
- **Statsmodels**: 时间序列分析
- **Matplotlib/Seaborn**: 数据可视化

## 注意事项

1. 确保数据文件 `FFA - tradetape - EEX.xlsx` 存在
2. 预测结果基于历史数据，实际市场可能有所不同
3. 建议定期重新训练模型以保持预测准确性
4. 长期预测（30天）准确率较低，建议谨慎使用

## 许可证

MIT License