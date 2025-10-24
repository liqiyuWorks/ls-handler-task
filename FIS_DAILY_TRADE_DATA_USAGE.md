# FIS逐日交易数据爬取使用指南

## 概述

已成功优化`SpiderFisDailyTradeData`模型，现在支持通过`python main.py`命令运行，并支持C5TC、P4TC、P5TC三种合约的逐日交易数据爬取。

## 可用命令

### 1. 爬取所有三种合约数据
```bash
python main.py spider_fis_daily_trade_data
```

### 2. 爬取单个合约数据
```bash
# 爬取C5TC数据
python main.py spider_fis_daily_c5tc

# 爬取P4TC数据
python main.py spider_fis_daily_p4tc

# 爬取P5TC数据
python main.py spider_fis_daily_p5tc
```

## 注意事项

### 1. 排除navgreen目录
由于navgreen目录存在依赖问题，建议运行时排除该目录：
```bash
EXCLUDE_DIRECTORY=navgreen python main.py spider_fis_daily_trade_data
```

### 2. Token过期问题
当前所有API都返回401认证失败，这是因为FIS认证token已过期。需要更新token：

```bash
# 检查token状态
python check_token.py

# 更新token
python update_fis_token.py
```

## 数据存储

每个合约类型的数据会保存到对应的MongoDB集合中：

- **C5TC**: `fis_daily_c5tc_trade_data`
- **P4TC**: `fis_daily_p4tc_trade_data`  
- **P5TC**: `fis_daily_p5tc_trade_data`

## 数据格式

每个文档包含以下字段：
- `Date` - 日期（唯一键，格式：YYYY-MM-DD）
- `Open`, `Close`, `High`, `Low`, `Volume` - 交易数据
- `product_type` - 产品类型（C5TC/P4TC/P5TC）
- `created_at` - 创建时间

## API端点

- **C5TC**: `https://livepricing-prod2.azurewebsites.net/api/v1/chartData/1/405/F/null/null`
- **P4TC**: `https://livepricing-prod2.azurewebsites.net/api/v1/chartData/12/405/F/null/null`
- **P5TC**: `https://livepricing-prod2.azurewebsites.net/api/v1/chartData/39/405/F/null/null`

## 故障排除

### 1. 认证失败（401错误）
- 运行 `python update_fis_token.py` 更新token
- 确保token有足够的权限访问API

### 2. 数据库连接失败
- 检查MongoDB连接配置
- 确保数据库服务正在运行

### 3. 初始化错误
- 检查环境变量配置
- 确保所有依赖包已安装

## 日志信息

程序会输出详细的日志信息，包括：
- 爬虫初始化状态
- API请求详情
- 数据保存结果
- 错误信息和解决建议

## 示例输出

```
2025-10-24 21:00:44,521 - INFO: 开始爬取所有FIS逐日交易数据
2025-10-24 21:00:44,521 - INFO: 开始爬取 C5TC 数据
2025-10-24 21:00:44,521 - INFO: 正在请求 C5TC API: https://livepricing-prod2.azurewebsites.net/api/v1/chartData/1/405/F/null/null
2025-10-24 21:00:45,613 - ERROR: C5TC API认证失败 (401) - Token可能已过期
2025-10-24 21:00:45,614 - ERROR: 请运行 'python update_fis_token.py' 更新token
```

## 技术架构

- **主类**: `SpiderFisDailyTradeData` - 单个产品类型爬虫
- **批量类**: `SpiderAllFisDailyTradeData` - 所有产品类型批量爬虫
- **任务注册**: 通过`sub_task_dic.py`注册到main.py任务系统
- **数据存储**: MongoDB，使用Date字段作为唯一键
- **认证**: JWT Bearer Token认证
