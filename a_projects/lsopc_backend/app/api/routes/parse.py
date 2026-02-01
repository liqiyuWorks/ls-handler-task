# -*- coding: utf-8 -*-
"""Parse API 路由"""

import logging

from fastapi import APIRouter

from app.schemas.parse import ParseRequest, ParseResponse
from app.services.xpath_analyzer import XpathAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter()
analyzer = XpathAnalyzer()


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="按 XPath 解析 URL",
    description="使用 Playwright 访问目标 URL，等待 JS 执行后按 XPath 提取数据。",
)
def parse_url(request: ParseRequest) -> ParseResponse:
    """
    解析请求入口。

    :param request: 包含 url 和 xpath 的请求对象
    :return: 解析后的结果列表
    """
    # 业务逻辑已在 Pydantic 中校验，此处直接调用 Service
    logger.info("Parsing request for URL: %s with XPath: %s", request.url, request.xpath)

    data = analyzer.fetch_and_parse(request.url, request.xpath)
    return ParseResponse(status="success", count=len(data), results=data)
