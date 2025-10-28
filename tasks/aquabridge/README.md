# AquaBridge 任务模块

从金正网站抓取数据并存储到MongoDB的数据管道系统。

## 📁 目录结构

```
tasks/aquabridge/
├── modules/                  # 核心模块目录
│   ├── __init__.py          # 模块初始化文件
│   ├── browser_config.py     # 浏览器配置管理
│   ├── data_scraper.py      # 数据抓取器
│   ├── enhanced_formatter.py # 数据格式化器
│   ├── mongodb_storage.py   # MongoDB存储
│   ├── page_config.py       # 页面配置
│   ├── p4tc_parser.py       # P4TC数据解析器
│   └── session_manager.py  # 浏览器会话管理器
├── subtasks/                 # 子任务目录
│   ├── spider_jinzheng_pages2mgo.py  # 主爬虫任务
│   └── ...                  # 其他子任务
├── output/                  # 输出目录（自动生成）
├── sub_task_dic.py          # 任务字典配置
├── mongodb_config.json      # MongoDB配置
└── README.md                # 本文件
```

## 🎯 核心模块说明

### modules/browser_config.py
- **功能**: 管理不同环境的浏览器配置
- **支持**: Chromium（生产）、Firefox（测试）、WebKit（可选）
- **配置**: 自动根据环境选择合适的浏览器

### modules/data_scraper.py
- **功能**: 数据抓取核心逻辑
- **特性**: 支持多页面、多浏览器、自动登录
- **配置**: 通过 page_config.py 配置页面

### modules/session_manager.py
- **功能**: 浏览器会话管理
- **特性**: 单次登录，多页面复用
- **优势**: 提高效率，避免重复登录

### modules/enhanced_formatter.py
- **功能**: 数据格式化
- **支持**: FFA价格信号、P4TC现货应用决策
- **输出**: 结构化JSON数据

### modules/mongodb_storage.py
- **功能**: MongoDB数据存储
- **特性**: 自动索引、数据去重、批量操作
- **配置**: 通过 mongodb_config.json

### modules/p4tc_parser.py
- **功能**: P4TC页面数据解析
- **支持**: 交易建议、预测数据、收益统计
- **输出**: 结构化分析结果

## 🚀 使用方法

### 1. 配置MongoDB
编辑 `mongodb_config.json`:

```json
{
  "mongodb": {
    "enabled": true,
    "host": "your-host",
    "port": 27017,
    "database": "aquabridge",
    "username": "your-username",
    "password": "your-password"
  }
}
```

### 2. 运行任务

```python
from subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo

# 创建实例
spider = SpiderJinzhengPages2mgo()

# 运行所有页面（推荐稳定模式）
result = spider.run({
    'page_key': 'all',
    'browser': 'chromium',
    'headless': True,
    'stable_mode': True,
    'fast_mode': True
})

print(result)
```

### 3. 运行单个页面

```python
# 只抓取P4TC页面
result = spider.run({
    'page_key': 'p4tc_spot_decision',
    'browser': 'chromium',
    'headless': True
})
```

## 📝 支持的页面

- `p4tc_spot_decision`: P4TC现货应用决策
- `ffa_price_signals`: FFA价格信号

## ⚙️ 配置选项

- `page_key`: 页面标识（默认'all'）
- `browser`: 浏览器类型（chromium/firefox/webkit）
- `headless`: 是否无头模式（默认True）
- `save_file`: 是否保存文件（默认True）
- `store_mongodb`: 是否存储到MongoDB（默认True）
- `stable_mode`: 稳定模式（推荐，默认True）
- `fast_mode`: 快速模式（默认False）

## 📊 输出文件

数据存储在 `output/` 目录下：
- JSON格式：`{page_key}_data_{timestamp}.json`
- 同时存储到MongoDB（如果启用）

## 🔧 环境要求

- Python 3.8+
- Playwright: `pip install playwright`
- PyMongo: `pip install pymongo`
- 需要安装浏览器：`playwright install chromium firefox`
