# 船舶油耗预测模型报告

## 模型概述
- 训练的船型数量: 9
- 全局模型: 是

## 各船型模型性能

### BULK CARRIER
- 最佳模型: Random Forest
- MAE: 0.000
- RMSE: 0.000
- R²: 1.000
- MAPE: 0.0%
- 重要特征:
  1. relative_consumption: 0.9998
  2. 燃油效率: 0.0001
  3. 单位距离油耗(mt/nm): 0.0000
  4. 总油耗(mt): 0.0000
  5. 重油IFO(mt): 0.0000

### Bulk Carrier
- 最佳模型: Gradient Boosting
- MAE: 0.000
- RMSE: 0.002
- R²: 1.000
- MAPE: 0.0%
- 重要特征:
  1. relative_consumption: 0.9998
  2. 航行距离(nm): 0.0000
  3. 载重比: 0.0000
  4. 航行距离(nm)_scaled: 0.0000
  5. 轻油cp: 0.0000

### OPEN HATCH CARGO SHIP
- 最佳模型: Gradient Boosting
- MAE: 0.000
- RMSE: 0.002
- R²: 1.000
- MAPE: 0.0%
- 重要特征:
  1. relative_consumption: 0.9985
  2. speed_load_interaction: 0.0003
  3. 单位距离油耗(mt/nm): 0.0002
  4. 燃油效率: 0.0002
  5. weather_factor: 0.0001

### CHEMICAL/PRODUCTS TANKER
- 最佳模型: Random Forest
- MAE: 0.001
- RMSE: 0.003
- R²: 1.000
- MAPE: 0.2%
- 重要特征:
  1. relative_consumption: 0.9999
  2. 总油耗(mt): 0.0000
  3. 轻油MDO/MGO(mt): 0.0000
  4. admiralty_coefficient_scaled: 0.0000
  5. 航行距离(nm)_scaled: 0.0000

### GENERAL CARGO SHIP
- 最佳模型: Gradient Boosting
- MAE: 0.001
- RMSE: 0.004
- R²: 1.000
- MAPE: 0.2%
- 重要特征:
  1. relative_consumption: 0.9987
  2. 燃油效率: 0.0004
  3. 总油耗(mt): 0.0002
  4. 轻油cp: 0.0001
  5. 速度偏差: 0.0001

### General Cargo Ship
- 最佳模型: Random Forest
- MAE: 0.001
- RMSE: 0.003
- R²: 0.999
- MAPE: 0.3%
- 重要特征:
  1. relative_consumption: 0.9241
  2. 船舶总长度(m)_scaled: 0.0460
  3. 船舶总长度(m): 0.0226
  4. 载重比: 0.0009
  5. 航速cp: 0.0008

### CRUDE OIL TANKER
- 最佳模型: Ridge Regression
- MAE: 0.012
- RMSE: 0.018
- R²: 0.996
- MAPE: 1.2%
- 重要特征:
  1. relative_consumption: 0.3583
  2. heavy_fuel_ratio: 0.1445
  3. 单位距离油耗(mt/nm): 0.0610
  4. 载重状态_encoded: 0.0394
  5. load_factor: 0.0394

### OTHER
- 最佳模型: Gradient Boosting
- MAE: 0.002
- RMSE: 0.003
- R²: 1.000
- MAPE: 0.4%
- 重要特征:
  1. relative_consumption: 0.9513
  2. 重油IFO(mt): 0.0275
  3. 载重比_scaled: 0.0053
  4. 燃油效率: 0.0042
  5. 单位距离油耗(mt/nm): 0.0041

### Crude Oil Tanker
- 最佳模型: Ridge Regression
- MAE: 0.008
- RMSE: 0.019
- R²: 0.991
- MAPE: 0.9%
- 重要特征:
  1. 燃油效率: 0.0287
  2. 航行时间(hrs): 0.0261
  3. 总油耗(mt): 0.0221
  4. heavy_fuel_ratio: 0.0119
  5. 轻油MDO/MGO(mt): 0.0112
