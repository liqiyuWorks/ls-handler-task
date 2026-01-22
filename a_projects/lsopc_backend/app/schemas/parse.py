# -*- coding: utf-8 -*-
"""Parse 相关请求/响应模型"""

from typing import List

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    """XPath 解析请求"""

    url: str = Field(
        default="https://data.eastmoney.com/report",
        description="目标网页 URL",
    )
    xpath: str = Field(
        default="//*[@id='indexnewreport_table']/table/tbody/tr[1]/td[5]",
        description="用于提取数据的 XPath 表达式",
    )


class ParseResponse(BaseModel):
    """XPath 解析响应"""

    status: str
    count: int
    results: List[str]
