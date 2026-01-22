# -*- coding: utf-8 -*-
"""Parse API 路由"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.parse import ParseRequest, ParseResponse
from app.services.xpath_analyzer import XpathAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter()
analyzer = XpathAnalyzer()


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="按 XPath 解析 URL",
)
def parse(request: ParseRequest) -> ParseResponse:
    """
    使用 Playwright 访问目标 URL，等待 JS 执行后按 XPath 提取数据。

    - **url**: 目标网页 URL（如 https://data.eastmoney.com/report/）
    - **xpath**: XPath 表达式（如 //table//tr/td[1]）
    """
    if not request.url or not request.xpath:
        raise HTTPException(status_code=400, detail="URL 和 XPath 为必填")

    try:
        data = analyzer.fetch_and_parse(request.url, request.xpath)
        return ParseResponse(status="success", count=len(data), results=data)
    except Exception as e:
        logger.exception("API error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
