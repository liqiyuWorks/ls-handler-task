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
                text="现货应用决策",
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
            NavigationStep(
                selectors=[
                    ".bi-f-c > .bi-icon-change-button > .x-icon"
                ],
                description="展开单边策略研究菜单"
            ),
            NavigationStep(
                selectors=[
                    "text='价格信号'",
                    "div:has-text('价格信号')",
                    "div:nth-child(2) > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon"
                ],
                text="价格信号",
                description="展开价格信号菜单"
            ),
            NavigationStep(
                selectors=[
                    "text='单边价格信号汇总'",
                    "div:has-text('单边价格信号汇总')",
                    "div:nth-child(2) > div > div:nth-child(2) > .bi-custom-tree > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon"
                ],
                text="单边价格信号汇总",
                description="展开单边价格信号汇总"
            ),
            NavigationStep(
                selectors=[
                    "text='FFA'",
                    "div:has-text('FFA')",
                    "div:nth-child(3) > div > div:nth-child(2) > .bi-icon-change-button"
                ],
                text="FFA",
                description="点击FFA页面"
            )
        ],
        query_button_selectors=[
            "button:has-text('查询')",
            "button[type='submit']",
            ".query-button",
            "[class*='query']"
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
