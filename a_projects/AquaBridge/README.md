# AquaBridge 数据抓取器

基于 Playwright 的数据抓取工具，支持从 AquaBridge 网站抓取多个页面的数据。

## 文件说明

- `test_case_chromium.py` - 原始工作脚本，已验证可抓取P4TC现货应用决策数据
- `page_config.py` - 页面配置定义，支持多页面配置
- `data_scraper.py` - 新架构数据抓取器（需要进一步调试）
- `README.md` - 说明文档

## 使用方法

### 抓取P4TC现货应用决策数据
```bash
python test_case_chromium.py
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

## 依赖要求

```bash
pip install playwright
playwright install chromium
```

## 注意事项

- 原始脚本 `test_case_chromium.py` 已验证可正常工作
- 新架构 `data_scraper.py` 需要进一步调试
- 建议优先使用原始脚本，新架构作为扩展基础