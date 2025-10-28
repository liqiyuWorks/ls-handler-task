# AquaBridge 目录结构

## 📂 整理后的目录结构

```
tasks/aquabridge/
│
├── README.md                      # 模块说明文档
├── STRUCTURE.md                   # 本文件（目录结构说明）
├── __init__.py                    # 包初始化文件
├── sub_task_dic.py                # 任务字典配置
├── mongodb_config.json            # MongoDB配置
│
├── modules/                        # 核心模块目录
│   ├── __init__.py                # 模块包初始化
│   ├── browser_config.py          # 浏览器配置管理
│   ├── data_scraper.py            # 数据抓取器
│   ├── enhanced_formatter.py      # 数据格式化器
│   ├── mongodb_storage.py         # MongoDB存储
│   ├── page_config.py             # 页面配置
│   ├── p4tc_parser.py             # P4TC数据解析器
│   └── session_manager.py         # 浏览器会话管理器
│
├── subtasks/                      # 子任务目录
│   ├── spider_jinzheng_pages2mgo.py  # 主爬虫任务
│   └── ...                         # 其他子任务
│
└── output/                        # 输出目录（自动生成）
    └── .gitignore                  # 忽略输出文件
```

## 📊 模块功能分类

### 核心模块 (modules/)

| 文件 | 行数 | 主要功能 |
|------|------|---------|
| browser_config.py | ~220 | 浏览器配置管理，支持多浏览器 |
| data_scraper.py | ~611 | 数据抓取核心逻辑 |
| enhanced_formatter.py | ~362 | 数据格式化 |
| mongodb_storage.py | ~491 | MongoDB存储操作 |
| page_config.py | ~146 | 页面配置定义 |
| p4tc_parser.py | ~578 | P4TC数据解析 |
| session_manager.py | ~267 | 浏览器会话管理 |

### 配置文件

| 文件 | 用途 |
|------|------|
| sub_task_dic.py | 定义可用的任务 |
| mongodb_config.json | MongoDB连接配置 |

### 子任务 (subtasks/)

| 文件 | 功能 |
|------|------|
| spider_jinzheng_pages2mgo.py | 主爬虫任务，整合所有模块 |

## 🎯 整理优化

### 1. 目录结构优化
- ✅ 核心模块集中到 `modules/` 目录
- ✅ 子任务文件保留在 `subtasks/` 目录
- ✅ 配置文件保留在根目录

### 2. 导入路径优化
- ✅ 使用相对导入 `from .module import ...`
- ✅ 保留向后兼容的绝对导入
- ✅ 添加了 `__init__.py` 使目录成为Python包

### 3. 文件组织
- ✅ 按功能分类（抓取、格式化、存储、配置）
- ✅ 相关模块放在同一目录
- ✅ 清晰的文件命名

### 4. 文档完善
- ✅ 添加 README.md 说明使用方法
- ✅ 添加 STRUCTURE.md 说明目录结构
- ✅ 代码中包含详细注释

## 🔗 模块依赖关系

```
subtasks/spider_jinzheng_pages2mgo.py
    ├── modules/session_manager.py
    │       ├── modules/data_scraper.py
    │       │   ├── modules/page_config.py
    │       │   └── modules/browser_config.py
    │       └── modules/page_config.py
    ├── modules/enhanced_formatter.py
    │   └── modules/p4tc_parser.py
    └── modules/mongodb_storage.py
```

## 📝 使用示例

### 基本使用

```python
from subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo

spider = SpiderJinzhengPages2mgo()

# 抓取所有页面
result = spider.run({
    'page_key': 'all',
    'browser': 'chromium',
    'headless': True,
    'stable_mode': True
})
```

### 只抓取特定页面

```python
# 只抓取 P4TC 页面
result = spider.run({
    'page_key': 'p4tc_spot_decision',
    'browser': 'chromium'
})
```

## 🚀 下一步优化建议

1. **代码重构**
   - 将超长文件拆分（如 p4tc_parser.py 578行）
   - 提取公共工具类

2. **测试完善**
   - 添加单元测试
   - 添加集成测试

3. **配置管理**
   - 使用配置类替代 JSON
   - 支持环境变量覆盖

4. **日志系统**
   - 统一日志格式
   - 添加日志轮转

5. **文档更新**
   - API 文档
   - 使用示例
   - 故障排除指南
