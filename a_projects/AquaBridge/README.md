# AquaBridge 数据抓取器

基于 Playwright 的自动化数据抓取工具，支持从 AquaBridge 网站抓取多个页面的数据。

**✨ 特性**: 支持多浏览器配置，生产环境使用 Chromium，测试环境使用 Firefox。

---

## 📁 目录结构

```
AquaBridge/
├── data_scraper.py          # 核心数据抓取器
├── page_config.py           # 页面配置定义
├── browser_config.py        # 浏览器配置模块
├── test_case_chromium.py    # 原始工作脚本（参考）
├── output/                  # 数据输出文件夹
│   ├── *.json              # JSON格式数据
│   └── *.txt               # TXT格式数据
├── docs/                    # 文档文件夹
│   ├── README.md           # 项目说明
│   ├── BROWSER_CONFIGURATION.md  # 浏览器配置指南
│   └── ...                 # 其他文档
├── tools/                   # 工具文件夹
│   ├── example_usage.py    # 使用示例
│   └── test_suite.py       # 测试套件
└── archive/                 # 归档文件夹
    ├── debug_*.py          # 调试脚本
    ├── *.png               # 调试截图
    └── *.log               # 调试日志
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip install playwright
playwright install chromium firefox
```

### 基本使用

```bash
# 抓取 P4TC 现货应用决策数据（生产环境，Chromium）
python3 data_scraper.py p4tc_spot_decision

# 抓取 FFA 价格信号数据（测试环境，Firefox）
python3 data_scraper.py ffa_price_signals --browser firefox

# 显示浏览器窗口（调试模式）
python3 data_scraper.py ffa_price_signals --browser firefox --no-headless
```

---

## 📊 支持的页面

| 页面 | 键值 | 描述 | 状态 |
|------|------|------|------|
| P4TC现货应用决策 | `p4tc_spot_decision` | P4TC现货策略的应用决策数据 | ✅ 已验证 |
| FFA价格信号 | `ffa_price_signals` | 单边价格信号汇总下的FFA数据 | ✅ 已验证 |

---

## 🔧 浏览器配置

### 环境配置

| 环境 | 浏览器 | 命令示例 |
|------|--------|----------|
| 生产环境 | Chromium（默认） | `python3 data_scraper.py` |
| 测试环境 | Firefox | `python3 data_scraper.py --env testing` |
| 开发调试 | 任意 + 显示窗口 | `python3 data_scraper.py --no-headless` |

### 命令行参数

```bash
python3 data_scraper.py [页面键] [选项]

选项:
  --browser {chromium,firefox,webkit}  浏览器类型
  --env {production,testing,development}  环境类型
  --headless                          无头模式
  --no-headless                       显示浏览器窗口
  -h, --help                         显示帮助
```

---

## 📂 输出文件

所有数据文件自动保存到 `output/` 文件夹：

- **JSON 格式**: 包含完整的元数据和统计信息
- **TXT 格式**: 便于直接查看的表格数据

文件命名格式：`{页面键}_data_{时间戳}.{扩展名}`

---

## 🛠️ 工具和测试

### 运行测试

```bash
python3 tools/test_suite.py
```

### 查看使用示例

```bash
python3 tools/example_usage.py
```

### 查看详细文档

- [浏览器配置指南](docs/BROWSER_CONFIGURATION.md)
- [完整测试报告](docs/TEST_REPORT.md)
- [故障排除指南](docs/FFA_TROUBLESHOOTING.md)

---

## 📝 添加新页面

在 `page_config.py` 中添加新的页面配置：

```python
"new_page_key": PageConfig(
    name="新页面名称",
    description="页面描述",
    navigation_path=[
        NavigationStep(
            selectors=["text='菜单项'"],
            description="点击菜单项"
        )
    ],
    query_button_selectors=["button:has-text('查询')"],
    data_extraction_config={
        "max_rows": 100,
        "max_cells": 20,
        "wait_after_query": 3
    }
)
```

---

## 🔍 故障排除

### 常见问题

1. **浏览器未安装**
   ```bash
   playwright install chromium firefox
   ```

2. **抓取失败**
   - 检查网络连接
   - 使用 `--no-headless` 查看浏览器窗口
   - 查看 `archive/` 文件夹中的调试日志

3. **页面配置问题**
   - 参考 `docs/` 文件夹中的故障排除指南
   - 使用 `archive/` 文件夹中的调试工具

---

## 📚 文档

- [README.md](docs/README.md) - 项目详细说明
- [浏览器配置指南](docs/BROWSER_CONFIGURATION.md) - 多浏览器配置详解
- [测试报告](docs/TEST_REPORT.md) - 完整测试结果
- [故障排除](docs/FFA_TROUBLESHOOTING.md) - 问题解决指南

---

## ✅ 状态

- ✅ 所有核心功能已验证
- ✅ 多浏览器支持完整
- ✅ 文档完整详细
- ✅ 生产环境就绪

---

**最后更新**: 2025-10-12  
**版本**: 2.0  
**状态**: 生产就绪
