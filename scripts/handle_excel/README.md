# Excel 回测数据处理脚本

## 功能说明

此脚本用于解析 `回测数据` 目录下的 Excel 文件，并根据文件名自动判断存储到对应的 MongoDB 集合中。

### 集合映射规则

脚本会**按合约类型**创建独立的集合，每个合约类型对应一个集合：
- `backtest_P5_historical_forecast_data` - P5 合约数据
- `backtest_P3A_historical_forecast_data` - P3A 合约数据
- `backtest_P6_historical_forecast_data` - P6 合约数据
- `backtest_C3_historical_forecast_data` - C3 合约数据
- `backtest_C5_historical_forecast_data` - C5 合约数据

集合名称格式：`backtest_{合约类型}_historical_forecast_data`

## 使用方法

### 方法 1: 使用运行脚本（推荐）

```bash
cd /path/to/ls-handler-task
./scripts/handle_excel/run_deal_xlsx.sh
```

这个脚本会自动：
1. 加载 MongoDB 环境变量配置（从 `env/aquabridge/.once_spider_jinzheng_pages2mgo.sh`）
2. 运行 Python 处理脚本

### 方法 2: 手动设置环境变量后运行

```bash
# 加载环境变量
source env/aquabridge/.once_spider_jinzheng_pages2mgo.sh

# 运行脚本
python3 scripts/handle_excel/deal_xlsx.py
```

### 方法 3: 直接运行（使用默认配置）

如果环境变量未设置，脚本会使用默认的 MongoDB 配置：
- Host: 153.35.96.86
- Port: 27017
- Database: aquabridge
- User: aquabridge
- Password: Aquabridge#2025

```bash
python3 scripts/handle_excel/deal_xlsx.py
```

## MongoDB 配置

脚本会从以下环境变量读取 MongoDB 配置：
- `MONGO_HOST`: MongoDB 主机地址
- `MONGO_PORT`: MongoDB 端口
- `MONGO_DB`: 数据库名称
- `MONGO_USER`: 用户名
- `MONGO_PASSWORD`: 密码

## 数据格式

Excel 文件应包含以下列：
- `日期`: 日期字段
- `实际价格`: 实际价格
- `XX天前预测价格`: 预测价格（其中 XX 为 14 或 42）

## 存储的数据结构

每个集合存储对应合约类型的数据，每条记录包含：
- `_id`: 唯一标识（日期，格式：YYYY-MM-DD）
- `date`: 日期（YYYY-MM-DD 格式）
- `contract_type`: 合约类型（如 P5, P3A, P6, C3, C5）
- `actual_price`: 实际价格（整数，可能为 null）
- `forecast_42d`: 42天前预测价格（整数，可能为 null）
- `forecast_14d`: 14天前预测价格（整数，可能为 null）

**重要说明**：
- 脚本会自动合并同一合约类型的42天和14天预测数据
- 同一天的记录会合并为一条，包含 `forecast_42d` 和 `forecast_14d` 两个字段
- 唯一键是 `date`（日期），每个集合中同一日期只有一条记录
- 所有价格字段都是**整数**类型（四舍五入）

**数据示例**：
```json
{
  "_id": "2025-12-31",
  "date": "2025-12-31",
  "contract_type": "P5",
  "actual_price": 18575,
  "forecast_42d": 16835,
  "forecast_14d": 17156
}
```

## 索引

脚本会自动创建以下索引：
- `date` 唯一索引（确保每个日期只有一条记录）
- `contract_type` 索引（便于查询）

## 日志

脚本会输出详细的处理日志，包括：
- 文件解析进度
- 数据存储状态
- 错误信息

## 文件映射示例

| 文件名 | 合约类型 | 预测天数 | 目标集合 |
|--------|---------|---------|---------|
| P3A-2025-历史预测（14天后）_预测价格数据详情.xlsx | P3A | 14天 | backtest_P3A_historical_forecast_data |
| P3A-2025历史预测（42天后）_预测价格数据详情.xlsx | P3A | 42天 | backtest_P3A_historical_forecast_data |
| C3-2025-历史预测_预测价格数据详情.xlsx | C3 | 42天 | backtest_C3_historical_forecast_data |
| P5-2025-历史预测（42天后）_预测价格数据详情.xlsx | P5 | 42天 | backtest_P5_historical_forecast_data |
| P5-2025-历史预测（14天后）_预测价格数据详情.xlsx | P5 | 14天 | backtest_P5_historical_forecast_data |

**注意**：同一合约类型的42天和14天预测数据会被合并到同一个集合中。

## 注意事项

1. 确保 MongoDB 连接正常
2. 确保 `回测数据` 目录下存在 Excel 文件（.xlsx 或 .xls）
3. 如果数据已存在，脚本会更新现有记录（基于日期）
4. 每个合约类型的集合中，**日期（date）作为唯一键**
5. 脚本会自动合并同一合约类型的42天和14天预测数据到同一个集合
6. 如果某个日期只有42天或14天的预测数据，另一个字段将为 null

