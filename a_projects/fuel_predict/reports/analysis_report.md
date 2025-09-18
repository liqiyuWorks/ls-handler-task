
# 船舶油耗数据分析报告

## 1. 数据概览
- 总记录数: 57,750 条
- 船舶数量: 1226 艘
- 数据时间范围: 2022-01-10 至 2026-06-24

## 2. 船型分布
- BULK CARRIER: 37682 条记录
- Bulk Carrier: 8600 条记录
- OPEN HATCH CARGO SHIP: 5862 条记录
- CHEMICAL/PRODUCTS TANKER: 2296 条记录
- GENERAL CARGO SHIP: 1296 条记录
- CRUDE OIL TANKER: 596 条记录
- General Cargo Ship: 586 条记录
- OTHER: 148 条记录
- Chemical/Products Tanker: 73 条记录
- Crude Oil Tanker: 71 条记录
- tanker: 36 条记录
- other: 31 条记录
- CONTAINER SHIP: 23 条记录
- Container Ship: 20 条记录
- BULK/CAUSTIC SODA CARRIER (CABU): 19 条记录
- GENERAL CARGO SHIP (OPEN HATCH): 9 条记录
- PRODUCTS TANKER: 5 条记录
- HEAVY LOAD CARRIER: 2 条记录

## 3. 载重状态分布
- Laden: 40680 条记录
- Ballast: 17070 条记录

## 4. 速度与油耗相关性分析

### General Cargo Ship
- 样本数: 523
- 速度与小时油耗相关性: 0.197
- 平均速度: 10.72 kts
- 平均小时油耗: 0.527 mt/h

### OPEN HATCH CARGO SHIP
- 样本数: 5194
- 速度与小时油耗相关性: 0.134
- 平均速度: 12.77 kts
- 平均小时油耗: 1.057 mt/h

### BULK CARRIER
- 样本数: 32795
- 速度与小时油耗相关性: 0.04
- 平均速度: 11.16 kts
- 平均小时油耗: 0.988 mt/h

### Bulk Carrier
- 样本数: 7447
- 速度与小时油耗相关性: 0.091
- 平均速度: 11.69 kts
- 平均小时油耗: 1.052 mt/h

### CHEMICAL/PRODUCTS TANKER
- 样本数: 1722
- 速度与小时油耗相关性: -0.018
- 平均速度: 10.6 kts
- 平均小时油耗: 0.854 mt/h

### GENERAL CARGO SHIP
- 样本数: 1154
- 速度与小时油耗相关性: 0.584
- 平均速度: 11.1 kts
- 平均小时油耗: 0.698 mt/h

### Chemical/Products Tanker
- 样本数: 69
- 速度与小时油耗相关性: 0.525
- 平均速度: 8.67 kts
- 平均小时油耗: 1.937 mt/h

### CRUDE OIL TANKER
- 样本数: 544
- 速度与小时油耗相关性: -0.25
- 平均速度: 10.7 kts
- 平均小时油耗: 1.814 mt/h

### tanker
- 样本数: 35
- 速度与小时油耗相关性: 0.744
- 平均速度: 11.2 kts
- 平均小时油耗: 2.524 mt/h

### OTHER
- 样本数: 140
- 速度与小时油耗相关性: 0.218
- 平均速度: 8.59 kts
- 平均小时油耗: 0.565 mt/h

### Crude Oil Tanker
- 样本数: 67
- 速度与小时油耗相关性: 0.337
- 平均速度: 10.47 kts
- 平均小时油耗: 1.157 mt/h

### Container Ship
- 样本数: 18
- 速度与小时油耗相关性: -0.101
- 平均速度: 9.48 kts
- 平均小时油耗: 0.436 mt/h

### other
- 样本数: 27
- 速度与小时油耗相关性: -0.26
- 平均速度: 11.22 kts
- 平均小时油耗: 0.472 mt/h

### BULK/CAUSTIC SODA CARRIER (CABU)
- 样本数: 18
- 速度与小时油耗相关性: 0.357
- 平均速度: 11.04 kts
- 平均小时油耗: 1.026 mt/h

### CONTAINER SHIP
- 样本数: 21
- 速度与小时油耗相关性: 0.12
- 平均速度: 8.5 kts
- 平均小时油耗: 0.268 mt/h

## 5. 关键发现和建议
- 不同船型的油耗特征存在显著差异，需要建立分船型的预测模型
- 速度与油耗呈现非线性关系，建议在模型中考虑速度的二次项或三次项
- 载重状态对油耗有重要影响，满载状态下油耗通常更高
- CP条款中的航速与实际航速存在差异，需要在预测中考虑这种偏差
