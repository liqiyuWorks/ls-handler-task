"""
页面配置模块
定义不同页面的导航路径和选择器
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class NavigationStep:
    """导航步骤配置"""
    selectors: List[str]  # 多个选择器，按优先级排序
    text: Optional[str] = None  # 文本匹配（用于文本链接）
    wait_time: float = 0.3  # 等待时间
    description: str = ""  # 描述信息


@dataclass
class PageConfig:
    """页面配置"""
    name: str  # 页面名称
    description: str  # 页面描述
    navigation_path: List[NavigationStep]  # 导航路径
    query_button_selectors: List[str]  # 查询按钮选择器
    data_extraction_config: dict  # 数据提取配置
    screenshot_config: Optional[dict] = None  # 截图配置，如果为None则表示不需要截图


# 页面配置定义
PAGE_CONFIGS = {
    "p4tc_spot_decision": PageConfig(
        name="P4TC现货应用决策",
        description="P4TC现货策略的应用决策数据",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon",
                    "div:nth-child(2) > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
                    "div:nth-child(2) > div > div:nth-child(2) > .bi-custom-tree > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
                    "div:nth-child(3) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon"
                ],
                description="展开现货策略菜单"
            ),
            NavigationStep(
                selectors=["text='现货应用决策'"],
                description="点击现货应用决策"
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 100,
            "max_cells": 20,
            "wait_after_query": 3
        }
    ),
    
    "ffa_price_signals": PageConfig(
        name="FFA价格信号",
        description="单边价格信号汇总下的FFA数据",
        navigation_path=[
            # 根据截图确认的导航路径：
            # AquaBridge -> 单边策略研究 -> 价格信号 -> 单边价格信号汇总 -> FFA
            # 使用与 P4TC 类似的策略，先尝试展开，再点击文本
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单（类似P4TC）",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='价格信号'",
                    "*:has-text('价格信号')",
                    ".bi-icon-change-button:has-text('价格信号')"
                ],
                description="展开价格信号菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边价格信号汇总'",
                    "*:has-text('单边价格信号汇总')",
                    ".bi-icon-change-button:has-text('单边价格信号汇总')"
                ],
                description="展开单边价格信号汇总",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='FFA'",
                    "*:has-text('FFA')",
                    ".bi-list-item:has-text('FFA')"
                ],
                description="点击FFA页面",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button:has-text('Query')",
            "button[type='submit']",
            "[class*='query']",
            "[class*='search']"
        ],
        data_extraction_config={
            "max_rows": 100,
            "max_cells": 20,
            "wait_after_query": 5
        }
    ),
    
    "european_line_signals": PageConfig(
        name="欧线价格信号",
        description="单边价格信号汇总下的欧线数据",
        navigation_path=[
            # 导航路径：单边策略研究 -> 价格信号 -> 单边价格信号汇总 -> 欧线
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='价格信号'",
                    "*:has-text('价格信号')",
                    ".bi-icon-change-button:has-text('价格信号')"
                ],
                description="展开价格信号菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边价格信号汇总'",
                    "*:has-text('单边价格信号汇总')",
                    ".bi-icon-change-button:has-text('单边价格信号汇总')"
                ],
                description="展开单边价格信号汇总",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='欧线'",
                    "*:has-text('欧线')",
                    ".bi-list-item:has-text('欧线')"
                ],
                description="点击欧线页面",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button:has-text('Query')",
            "button[type='submit']",
            "[class*='query']",
            "[class*='search']"
        ],
        data_extraction_config={
            "max_rows": 100,
            "max_cells": 20,
            "wait_after_query": 5
        }
    ),
    
    "trading_opportunity_42d": PageConfig(
        name="交易机会汇总（42天后）",
        description="单边价格信号汇总下的交易机会汇总（42天后）数据",
        navigation_path=[
            # 导航路径：单边策略研究 -> 价格信号 -> 单边价格信号汇总 -> 交易机会汇总（42天后）
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='价格信号'",
                    "*:has-text('价格信号')",
                    ".bi-icon-change-button:has-text('价格信号')"
                ],
                description="展开价格信号菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边价格信号汇总'",
                    "*:has-text('单边价格信号汇总')",
                    ".bi-icon-change-button:has-text('单边价格信号汇总')"
                ],
                description="展开单边价格信号汇总",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='交易机会汇总（42天后）'",
                    "*:has-text('交易机会汇总（42天后）')",
                    "*:has-text('交易机会汇总')",
                    ".bi-list-item:has-text('交易机会汇总')"
                ],
                description="点击交易机会汇总（42天后）页面",
                wait_time=2.0
            )
        ],
        query_button_selectors=[],  # 截图模式不需要查询按钮
        data_extraction_config={
            "max_rows": 100,
            "max_cells": 20,
            "wait_after_query": 0  # 截图模式不需要等待查询
        },
        screenshot_config={
            "enabled": True,
            "element_selectors": [
                "div[widgetname='REPORT1']",
                "div[widgetname*='REPORT']:nth-of-type(2)",
                "div:has-text('期货')",
                "div[class*='widget']:nth-of-type(2)",
                "div[class*='report']:nth-of-type(2)"
            ],
            "wait_before_screenshot": 8,  # 增加等待时间确保页面完全加载
            "output_dir": "output/screenshots"
        }
    ),
    
    # P5现货应用决策页面配置
    "p5_spot_decision_42d": PageConfig(
        name="P5现货应用决策（42天后）",
        description="P5现货策略的应用决策数据（42天后）",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='P5现货'",
                    "*:has-text('P5现货')",
                    ".bi-icon-change-button:has-text('P5现货')"
                ],
                description="展开P5现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策（42天后）'",
                    "*:has-text('现货应用决策（42天后）')",
                    ".bi-list-item:has-text('现货应用决策（42天后）')"
                ],
                description="点击现货应用决策（42天后）",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 200,  # 增加行数限制以捕获更多表格数据
            "max_cells": 30,  # 增加单元格限制以捕获更宽的表格
            "wait_after_query": 5  # 增加等待时间确保数据完全加载
        }
    ),
    
    "p5_spot_decision_14d": PageConfig(
        name="P5现货应用决策（14天后）",
        description="P5现货策略的应用决策数据（14天后）",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='P5现货'",
                    "*:has-text('P5现货')",
                    ".bi-icon-change-button:has-text('P5现货')"
                ],
                description="展开P5现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策（14天后）'",
                    "*:has-text('现货应用决策（14天后）')",
                    ".bi-list-item:has-text('现货应用决策（14天后）')"
                ],
                description="点击现货应用决策（14天后）",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 100,
            "max_cells": 20,
            "wait_after_query": 3
        }
    ),
    
    # P3A现货应用决策页面配置
    "p3a_spot_decision_42d": PageConfig(
        name="P3A现货应用决策（42天后）",
        description="P3A现货策略的应用决策数据（42天后）",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='P3A现货'",
                    "*:has-text('P3A现货')",
                    ".bi-icon-change-button:has-text('P3A现货')"
                ],
                description="展开P3A现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策（42天后）'",
                    "*:has-text('现货应用决策（42天后）')",
                    ".bi-list-item:has-text('现货应用决策（42天后）')"
                ],
                description="点击现货应用决策（42天后）",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 200,  # 增加行数限制以捕获更多表格数据
            "max_cells": 30,  # 增加单元格限制以捕获更宽的表格
            "wait_after_query": 5  # 增加等待时间确保数据完全加载
        }
    ),
    
    "p3a_spot_decision_14d": PageConfig(
        name="P3A现货应用决策（14天后）",
        description="P3A现货策略的应用决策数据（14天后）",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='P3A现货'",
                    "*:has-text('P3A现货')",
                    ".bi-icon-change-button:has-text('P3A现货')"
                ],
                description="展开P3A现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策（14天后）'",
                    "*:has-text('现货应用决策（14天后）')",
                    ".bi-list-item:has-text('现货应用决策（14天后）')"
                ],
                description="点击现货应用决策（14天后）",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 200,  # 增加行数限制以捕获更多表格数据
            "max_cells": 30,  # 增加单元格限制以捕获更宽的表格
            "wait_after_query": 5  # 增加等待时间确保数据完全加载
        }
    ),
    
    # P6现货应用决策页面配置
    "p6_spot_decision_42d": PageConfig(
        name="P6现货应用决策（42天后）",
        description="P6现货策略的应用决策数据（42天后）",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='P6现货'",
                    "*:has-text('P6现货')",
                    ".bi-icon-change-button:has-text('P6现货')"
                ],
                description="展开P6现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策（42天后）'",
                    "*:has-text('现货应用决策（42天后）')",
                    ".bi-list-item:has-text('现货应用决策（42天后）')"
                ],
                description="点击现货应用决策（42天后）",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 200,  # 增加行数限制以捕获更多表格数据
            "max_cells": 30,  # 增加单元格限制以捕获更宽的表格
            "wait_after_query": 5  # 增加等待时间确保数据完全加载
        }
    ),
    
    "p6_spot_decision_14d": PageConfig(
        name="P6现货应用决策（14天后）",
        description="P6现货策略的应用决策数据（14天后）",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='P6现货'",
                    "*:has-text('P6现货')",
                    ".bi-icon-change-button:has-text('P6现货')"
                ],
                description="展开P6现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策（14天后）'",
                    "*:has-text('现货应用决策（14天后）')",
                    ".bi-list-item:has-text('现货应用决策（14天后）')"
                ],
                description="点击现货应用决策（14天后）",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 200,  # 增加行数限制以捕获更多表格数据
            "max_cells": 30,  # 增加单元格限制以捕获更宽的表格
            "wait_after_query": 5  # 增加等待时间确保数据完全加载
        }
    ),
    
    # C3现货应用决策页面配置
    "c3_spot_decision": PageConfig(
        name="C3现货应用决策",
        description="C3现货策略的应用决策数据",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='C3现货'",
                    "*:has-text('C3现货')",
                    ".bi-icon-change-button:has-text('C3现货')"
                ],
                description="展开C3现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策'",
                    "*:has-text('现货应用决策')",
                    ".bi-list-item:has-text('现货应用决策')"
                ],
                description="点击现货应用决策",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 200,  # 增加行数限制以捕获更多表格数据
            "max_cells": 30,  # 增加单元格限制以捕获更宽的表格
            "wait_after_query": 5  # 增加等待时间确保数据完全加载
        }
    ),
    
    # C5现货应用决策页面配置
    "c5_spot_decision": PageConfig(
        name="C5现货应用决策",
        description="C5现货策略的应用决策数据",
        navigation_path=[
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开主菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='单边策略研究'",
                    "*:has-text('单边策略研究')",
                    ".bi-icon-change-button:has-text('单边策略研究')"
                ],
                description="展开单边策略研究菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货策略'",
                    "*:has-text('现货策略')",
                    ".bi-icon-change-button:has-text('现货策略')"
                ],
                description="展开现货策略菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='C5现货'",
                    "*:has-text('C5现货')",
                    ".bi-icon-change-button:has-text('C5现货')"
                ],
                description="展开C5现货菜单",
                wait_time=1.0
            ),
            NavigationStep(
                selectors=[
                    "text='现货应用决策'",
                    "*:has-text('现货应用决策')",
                    ".bi-list-item:has-text('现货应用决策')"
                ],
                description="点击现货应用决策",
                wait_time=2.0
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']"
        ],
        data_extraction_config={
            "max_rows": 100,
            "max_cells": 20,
            "wait_after_query": 3
        }
    )
}


def get_page_config(page_key: str) -> Optional[PageConfig]:
    """获取页面配置"""
    return PAGE_CONFIGS.get(page_key)


def list_available_pages() -> List[str]:
    """列出所有可用的页面"""
    return list(PAGE_CONFIGS.keys())


def get_page_info() -> dict:
    """获取所有页面的基本信息"""
    return {
        key: {
            "name": config.name,
            "description": config.description
        }
        for key, config in PAGE_CONFIGS.items()
    }
