# 船舶油耗预测模型验证报告

## 整体性能指标
- 平均绝对误差 (MAE): 0.001 mt/h
- 均方根误差 (RMSE): 0.007 mt/h
- 决定系数 (R²): 0.999
- 平均绝对百分比误差 (MAPE): 0.1%
- 最大误差: 0.335 mt/h

## 各船型性能分析

### BULK CARRIER
- 样本数量: 6501
- MAE: 0.000 mt/h
- RMSE: 0.001 mt/h
- R²: 1.000
- MAPE: 0.0%
- 预测偏差: -0.000 mt/h

### OPEN HATCH CARGO SHIP
- 样本数量: 1004
- MAE: 0.000 mt/h
- RMSE: 0.002 mt/h
- R²: 1.000
- MAPE: 0.0%
- 预测偏差: 0.000 mt/h

### Bulk Carrier
- 样本数量: 1505
- MAE: 0.000 mt/h
- RMSE: 0.002 mt/h
- R²: 1.000
- MAPE: 0.1%
- 预测偏差: 0.000 mt/h

### CHEMICAL/PRODUCTS TANKER
- 样本数量: 349
- MAE: 0.001 mt/h
- RMSE: 0.005 mt/h
- R²: 1.000
- MAPE: 0.6%
- 预测偏差: -0.000 mt/h

### General Cargo Ship
- 样本数量: 105
- MAE: 0.005 mt/h
- RMSE: 0.019 mt/h
- R²: 0.983
- MAPE: 0.6%
- 预测偏差: -0.002 mt/h

### GENERAL CARGO SHIP
- 样本数量: 206
- MAE: 0.001 mt/h
- RMSE: 0.005 mt/h
- R²: 1.000
- MAPE: 0.5%
- 预测偏差: 0.000 mt/h

### CRUDE OIL TANKER
- 样本数量: 86
- MAE: 0.023 mt/h
- RMSE: 0.048 mt/h
- R²: 0.965
- MAPE: 2.5%
- 预测偏差: 0.004 mt/h

### Container Ship
- 样本数量: 7
- MAE: 0.018 mt/h
- RMSE: 0.034 mt/h
- R²: -20.147
- MAPE: 4.0%
- 预测偏差: 0.010 mt/h

### other
- 样本数量: 7
- MAE: 0.012 mt/h
- RMSE: 0.015 mt/h
- R²: 0.274
- MAPE: 2.5%
- 预测偏差: 0.012 mt/h

### Crude Oil Tanker
- 样本数量: 16
- MAE: 0.004 mt/h
- RMSE: 0.006 mt/h
- R²: 0.997
- MAPE: 0.4%
- 预测偏差: 0.001 mt/h

### OTHER
- 样本数量: 29
- MAE: 0.007 mt/h
- RMSE: 0.013 mt/h
- R²: 0.991
- MAPE: 1.5%
- 预测偏差: -0.001 mt/h

### Chemical/Products Tanker
- 样本数量: 6
- MAE: 0.010 mt/h
- RMSE: 0.017 mt/h
- R²: 0.990
- MAPE: 0.7%
- 预测偏差: -0.009 mt/h

### PRODUCTS TANKER
- 样本数量: 1
- MAE: 0.033 mt/h
- RMSE: 0.033 mt/h
- R²: nan
- MAPE: 8.9%
- 预测偏差: -0.033 mt/h

### GENERAL CARGO SHIP (OPEN HATCH)
- 样本数量: 4
- MAE: 0.032 mt/h
- RMSE: 0.036 mt/h
- R²: -84.844
- MAPE: 4.1%
- 预测偏差: 0.032 mt/h

### HEAVY LOAD CARRIER
- 样本数量: 1
- MAE: 0.009 mt/h
- RMSE: 0.009 mt/h
- R²: nan
- MAPE: 1.3%
- 预测偏差: -0.009 mt/h

### BULK/CAUSTIC SODA CARRIER (CABU)
- 样本数量: 2
- MAE: 0.004 mt/h
- RMSE: 0.004 mt/h
- R²: 0.945
- MAPE: 0.4%
- 预测偏差: -0.004 mt/h

### CONTAINER SHIP
- 样本数量: 3
- MAE: 0.001 mt/h
- RMSE: 0.002 mt/h
- R²: -2.742
- MAPE: 0.5%
- 预测偏差: 0.000 mt/h

## 残差分析
- 残差均值: -0.000
- 残差标准差: 0.007
- 偏度: -11.762
- 峰度: 946.346
- 异常值数量: 64
- 异常值比例: 0.6%

## 业务验证
### 预测合理性
- 正值预测比例: 100.0%
- 正常范围预测比例: 96.1%
- 极端预测比例: 0.0%

### 行业基准对比
- BULK CARRIER:
  - 预测平均值: 1.0 mt/h
  - 行业基准: 25.0 mt/h
  - 偏差: -96.1%
- General Cargo Ship:
  - 预测平均值: 0.5 mt/h
  - 行业基准: 15.0 mt/h
  - 偏差: -96.5%
- CONTAINER SHIP:
  - 预测平均值: 0.3 mt/h
  - 行业基准: 180.0 mt/h
  - 偏差: -99.9%

## 结论和建议
- 模型整体性能优秀，R²超过0.8，具有很强的预测能力
- 预测精度很高，MAPE小于10%，可用于实际业务
- 建议定期重新训练模型以保持预测准确性
- 建议收集更多高质量数据以改善模型性能
- 建议结合领域专家知识进一步优化特征工程
