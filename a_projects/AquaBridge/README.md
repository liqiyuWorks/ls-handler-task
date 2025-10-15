# AquaBridge 多页面数据管道

一个专注于多页面数据抓取、处理和存储的简约系统，支持 FFA价格信号 和 P4TC现货应用决策 两个页面的自动化数据处理。

## 核心功能

- ✅ **多页面支持**：FFA价格信号、P4TC现货应用决策
- ✅ **智能抓取**：基于 Playwright 的稳定数据抓取
- ✅ **会话复用**：优化版支持登录复用，提高效率50%
- ✅ **数据格式化**：自动转换为结构化 JSON 格式
- ✅ **独立存储**：每个页面使用独立的MongoDB collection
- ✅ **灵活配置**：支持多种运行模式和浏览器选择

## 快速开始

### 1. 安装依赖

```bash
pip3 install playwright pymongo
playwright install firefox
```

### 2. 配置 MongoDB

创建 `mongodb_config.json` 文件：

```json
{
  "mongodb": {
    "enabled": true,
    "host": "153.35.96.86",
    "port": 27017,
    "database": "aquabridge",
    "username": "aquabridge",
    "password": "Aquabridge#2025",
    "collection": "ffa_price_signals"
  }
}
```

### 3. 运行数据管道

```bash
# 处理所有页面（优化版本，推荐）
python3 aquabridge_pipeline.py --all

# 处理所有页面（传统版本，对比）
python3 aquabridge_pipeline.py --all-legacy

# 处理特定页面
python3 aquabridge_pipeline.py --page ffa_price_signals

# 仅存储到 MongoDB（不保存文件）
python3 aquabridge_pipeline.py --all --mongodb-only
```

## 使用方法

### 主管道命令

```bash
# 列出支持的页面
python3 aquabridge_pipeline.py --list

# 处理所有页面（显示浏览器窗口）
python3 aquabridge_pipeline.py --all --no-headless

# 处理特定页面（无头模式）
python3 aquabridge_pipeline.py --page p4tc_spot_decision --headless

# 禁用 MongoDB 存储
python3 aquabridge_pipeline.py --all --no-mongodb

# 仅存储到 MongoDB
python3 aquabridge_pipeline.py --all --mongodb-only
```

### MongoDB 管理

```bash
# 测试连接
python3 mongodb_cli.py test

# 列出所有页面的数据
python3 mongodb_cli.py list --limit 10

# 列出特定页面的数据
python3 mongodb_cli.py list --page ffa_price_signals --limit 5

# 获取特定日期的数据（所有页面）
python3 mongodb_cli.py get 2025-10-15

# 获取特定页面的数据
python3 mongodb_cli.py get 2025-10-15 --page ffa_price_signals

# 删除特定日期的数据
python3 mongodb_cli.py delete 2025-10-15

# 删除特定页面的数据
python3 mongodb_cli.py delete 2025-10-15 --page ffa_price_signals

# 显示所有页面的统计信息
python3 mongodb_cli.py stats

# 显示特定页面的统计信息
python3 mongodb_cli.py stats --page ffa_price_signals
```

## 数据格式

### FFA价格信号数据

```json
{
  "timestamp": "20251015_204602",
  "browser": "chromium",
  "page_name": "FFA价格信号",
  "swap_date": "2025-10-15",
  "contracts": {
    "C5TC+1": {
      "预测值": "35100",
      "当前值": "27250",
      "偏离度": "-22%",
      "入场区间": "<19300",
      "离场区间": ">29850",
      "操作建议": "持有多单/空仓"
    },
    "P4TC+1": {
      "预测值": "14450",
      "当前值": "14750",
      "偏离度": "2%",
      "入场区间": ">18750",
      "离场区间": "<15150",
      "操作建议": "平空/空仓"
    }
  },
  "stored_at": "2025-10-15T20:46:02.123456"
}
```

### P4TC现货应用决策数据

```json
{
  "timestamp": "20251015_204602",
  "browser": "chromium",
  "page_name": "P4TC现货应用决策",
  "swap_date": "2025-10-15",
  "contracts": {
    "table_data": {
      "rows": [...],
      "total_rows": 55,
      "description": "P4TC现货应用决策数据"
    }
  },
  "stored_at": "2025-10-15T20:46:02.123456"
}
```

## 项目结构

```
AquaBridge/
├── aquabridge_pipeline.py    # 主数据管道（优化版+传统版）
├── data_scraper.py          # 数据抓取器
├── enhanced_formatter.py    # 增强型数据格式化器
├── p4tc_parser.py          # P4TC专用数据解析器
├── session_manager.py       # 会话管理器（登录复用）
├── mongodb_storage.py       # MongoDB 存储模块
├── mongodb_cli.py          # MongoDB 命令行工具
├── page_config.py          # 页面配置
├── browser_config.py       # 浏览器配置
├── mongodb_config.json     # MongoDB 配置
├── output/                 # 数据输出目录
├── README.md              # 主文档
├── OPTIMIZATION_SUMMARY.md # 会话复用优化说明
├── P4TC_OPTIMIZATION_SUMMARY.md # P4TC解析优化说明
└── CLEANUP_SUMMARY.md     # 项目清理总结
```

## 命令行参数

### aquabridge_pipeline.py

| 参数 | 说明 |
|------|------|
| `--all` | 处理所有页面 |
| `--page` | 处理指定页面 |
| `--list` | 列出支持的页面 |
| `--browser` | 浏览器类型 (firefox/chromium/webkit) |
| `--headless` | 无头模式运行 |
| `--no-headless` | 显示浏览器窗口 |
| `--no-mongodb` | 禁用 MongoDB 存储 |
| `--mongodb-only` | 仅存储到 MongoDB |
| `--no-file` | 不保存到文件 |

### mongodb_cli.py

| 命令 | 说明 |
|------|------|
| `test` | 测试连接 |
| `list [--page PAGE]` | 列出数据（可选指定页面） |
| `get <date> [--page PAGE]` | 获取指定日期的数据（可选指定页面） |
| `delete <date> [--page PAGE]` | 删除指定日期的数据（可选指定页面） |
| `stats [--page PAGE]` | 显示统计信息（可选指定页面） |

## 特性

- **简约设计**：专注于核心功能，去除冗余代码
- **多页面支持**：统一处理不同页面的数据
- **独立存储**：每个页面使用独立的MongoDB collection
- **智能格式化**：根据页面类型自动选择格式化策略
- **稳定抓取**：基于 Playwright 的可靠数据抓取
- **灵活存储**：支持文件和数据库双重存储
- **易于扩展**：模块化设计，便于添加新页面

## 性能优化

### 会话复用机制
- **优化版本** (`--all`)：单次登录，多次页面抓取，效率提升50%
- **传统版本** (`--all-legacy`)：每个页面独立登录，用于对比

### 数据库结构

#### Collection 组织
- `ffa_price_signals_data`：FFA价格信号数据
- `p4tc_spot_decision_data`：P4TC现货应用决策数据

#### 索引设计
- `swap_date`：唯一索引，确保每个日期的数据唯一
- `timestamp`：查询索引，支持按时间排序
- `page_key`：页面标识，便于分类管理

#### 数据隔离
- 每个页面的数据存储在独立的collection中
- 便于独立管理和查询
- 支持页面级别的数据操作

## 故障排除

### 常见问题

1. **浏览器启动失败**
   ```bash
   playwright install firefox
   ```

2. **MongoDB 连接失败**
   - 检查网络连接
   - 验证配置文件
   - 确认服务状态

3. **数据抓取失败**
   - 检查网站可访问性
   - 验证登录凭据
   - 尝试不同浏览器

### 调试模式

```bash
# 显示详细日志
export PYTHONPATH=.
python3 -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python3 aquabridge_pipeline.py --all
```

## 扩展开发

### 添加新页面

1. 在 `page_config.py` 中添加页面配置
2. 在 `smart_formatter.py` 中添加格式化逻辑
3. 在 `aquabridge_pipeline.py` 中注册新页面

### 自定义格式化器

继承 `SmartFFAFormatter` 类并实现特定的数据提取逻辑。

## 许可证

MIT License