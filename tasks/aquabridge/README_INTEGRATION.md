# AquaBridge 集成说明

## 概述

已成功将 `aquabridge_pipeline.py` 的功能集成到 `spider_jinzheng_pages2mgo.py` 中，实现了完整的数据抓取、处理和存储功能。

## 功能特性

### 支持的页面
- **ffa_price_signals**: FFA价格信号页面
- **p4tc_spot_decision**: P4TC现货应用决策页面

### 主要功能
1. **数据抓取**: 使用 Playwright 自动化浏览器抓取页面数据
2. **数据格式化**: 使用增强型格式化器处理原始数据
3. **数据存储**: 支持 MongoDB 存储和本地文件保存
4. **会话管理**: 支持多页面复用登录会话，提高效率
5. **错误处理**: 完善的异常处理和日志记录

## 使用方法

### 基本用法

```python
from tasks.aquabridge.subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo

# 创建实例
spider = SpiderJinzhengPages2mgo()

# 处理所有页面
result = spider.run({'page_key': 'all'})

# 处理指定页面
result = spider.run({'page_key': 'ffa_price_signals'})
```

### 高级用法

```python
# 自定义配置
task = {
    'page_key': 'all',           # 或 'ffa_price_signals', 'p4tc_spot_decision'
    'browser': 'firefox',        # 'firefox', 'chromium', 'webkit'
    'headless': True,            # 是否无头模式
    'save_file': True,           # 是否保存到文件
    'store_mongodb': True        # 是否存储到MongoDB
}

result = spider.run(task)
```

### 直接调用方法

```python
# 处理单个页面
success = spider.process_page(
    page_key='ffa_price_signals',
    browser='firefox',
    headless=True,
    save_file=True,
    store_mongodb=True
)

# 处理所有页面（优化版本，复用登录）
results = spider.process_all_pages(
    browser='firefox',
    headless=True,
    save_file=True,
    store_mongodb=True
)

# 列出支持的页面
spider.list_supported_pages()
```

## 配置说明

### MongoDB 配置
配置文件位置: `tasks/aquabridge/mongodb_config.json`

```json
{
  "enabled": true,
  "host": "153.35.96.86",
  "port": 27017,
  "database": "aquabridge",
  "username": "aquabridge",
  "password": "Aquabridge#2025",
  "collection": "ffa_price_signals"
}
```

### 页面配置
- FFA页面配置: `page_config.py` 中的 `ffa_price_signals`
- P4TC页面配置: `page_config.py` 中的 `p4tc_spot_decision`

### 浏览器配置
支持的浏览器: `chromium`, `firefox`, `webkit`
默认配置在 `browser_config.py` 中定义

## 文件结构

```
tasks/aquabridge/
├── subtasks/
│   └── spider_jinzheng_pages2mgo.py    # 主入口文件
├── data_scraper.py                      # 数据抓取器
├── enhanced_formatter.py                # 数据格式化器
├── mongodb_storage.py                   # MongoDB存储
├── session_manager.py                   # 会话管理器
├── page_config.py                       # 页面配置
├── browser_config.py                    # 浏览器配置
├── p4tc_parser.py                       # P4TC解析器
├── mongodb_config.json                  # MongoDB配置
├── simple_test.py                       # 简化测试脚本
└── README_INTEGRATION.md                # 本说明文档
```

## 返回结果格式

### 成功处理所有页面
```python
{
    'status': 'success',
    'results': {
        'ffa_price_signals': True,
        'p4tc_spot_decision': True
    },
    'success_count': 2,
    'total_count': 2
}
```

### 成功处理单个页面
```python
{
    'status': 'success',
    'page_key': 'ffa_price_signals',
    'success': True
}
```

### 处理失败
```python
{
    'status': 'failed',
    'error': '错误信息'
}
```

## 测试验证

运行简化测试验证集成功能：

```bash
cd tasks/aquabridge
python3 simple_test.py
```

## 注意事项

1. **依赖包**: 需要安装 `playwright`, `pymongo` 等依赖包
2. **浏览器**: 需要安装 Playwright 浏览器: `playwright install`
3. **网络**: 需要能够访问目标网站和MongoDB服务器
4. **权限**: 确保有足够的文件写入权限

## 错误处理

- 所有方法都包含完善的异常处理
- 失败时会返回详细的错误信息
- 支持部分成功的情况（如一个页面成功，另一个失败）

## 性能优化

- 使用会话管理器复用登录状态，避免重复登录
- 支持批量处理多个页面
- 可配置的浏览器超时时间
- 智能的数据提取配置
