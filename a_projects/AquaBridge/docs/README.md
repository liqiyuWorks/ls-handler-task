# AquaBridge 数据抓取器

基于 Playwright 的数据抓取工具，支持从 AquaBridge 网站抓取多个页面的数据。

**✨ 新特性**: 现已支持多浏览器配置！生产环境使用 Chromium，测试环境使用 Firefox。

## 文件说明

### 核心文件
- `data_scraper.py` - 新架构数据抓取器（✅ 已测试，支持多浏览器）
- `page_config.py` - 页面配置定义，支持多页面配置
- `browser_config.py` - **浏览器配置模块（新）**
- `test_case_chromium.py` - 原始工作脚本，已验证可用

### 测试工具
- `test_suite.py` - 综合自动化测试套件
- `code_analysis.py` - 代码分析工具
- `test_live.py` - 实际网站测试脚本

### 文档
- `README.md` - 本文档
- `BROWSER_CONFIGURATION.md` - 浏览器配置详细指南
- `BROWSER_QUICK_REFERENCE.md` - 浏览器配置快速参考
- `TEST_REPORT.md` - 完整测试报告
- `QUICK_TEST_GUIDE.md` - 快速测试指南

## 快速开始

### 方式 1: 使用新架构（推荐）

#### 生产环境（Chromium，默认）
```bash
python3 data_scraper.py
```

#### 测试环境（Firefox）
```bash
python3 data_scraper.py --env testing
# 或
python3 data_scraper.py --browser firefox
```

#### 开发调试（显示浏览器窗口）
```bash
python3 data_scraper.py --no-headless
```

### 方式 2: 使用原始脚本
```bash
python3 test_case_chromium.py
```

### 添加新页面
在 `page_config.py` 中添加新的页面配置：

```python
"new_page_key": PageConfig(
    name="新页面名称",
    description="页面描述",
    navigation_path=[
        NavigationStep(
            selectors=["选择器1", "选择器2"],
            text="文本内容",
            description="步骤描述"
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

## 输出格式

数据会保存为JSON和TXT两种格式：
- JSON格式包含完整的元数据和统计信息
- TXT格式便于直接查看表格数据

## 浏览器配置

### 支持的浏览器

| 浏览器 | 推荐场景 | 命令 |
|--------|---------|------|
| Chromium | 生产环境（默认） | `python3 data_scraper.py` |
| Firefox | 测试环境 | `python3 data_scraper.py --env testing` |
| WebKit | 可选 | `python3 data_scraper.py --browser webkit` |

### 常用命令

```bash
# 生产环境（Chromium，无头模式）
python3 data_scraper.py

# 测试环境（Firefox）
python3 data_scraper.py --env testing

# 显示浏览器窗口（调试）
python3 data_scraper.py --no-headless

# Firefox + 显示窗口
python3 data_scraper.py --browser firefox --no-headless

# 抓取指定页面
python3 data_scraper.py ffa_price_signals --browser firefox

# 查看帮助
python3 data_scraper.py --help
```

详细配置说明请参考：`BROWSER_CONFIGURATION.md`

## 依赖要求

```bash
# 安装 Playwright
pip install playwright

# 安装浏览器（根据需要选择）
playwright install chromium  # 生产环境必需
playwright install firefox   # 测试环境推荐
playwright install webkit    # 可选

# 或一次性安装所有浏览器
playwright install
```

## 测试验证

```bash
# 1. 运行基础测试（推荐首先运行）
python3 test_suite.py

# 2. 测试浏览器配置
python3 browser_config.py

# 3. 代码分析
python3 code_analysis.py
```

## 注意事项

- ✅ 所有模块已通过测试验证（100% 测试通过率）
- ✅ 原始脚本 `test_case_chromium.py` 已验证可正常工作
- ✅ 新架构 `data_scraper.py` 已修复并测试通过
- 🎯 生产环境推荐使用 Chromium（默认配置）
- 🧪 测试环境推荐使用 Firefox 验证兼容性