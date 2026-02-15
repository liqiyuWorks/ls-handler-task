# -*- coding: utf-8 -*-
"""平台统一时间：库内存 UTC，接口返回带 Z 的 UTC ISO 字符串，前端按北京时间展示"""

from typing import Any


def utc_iso_for_api(dt: Any) -> str:
    """
    将 datetime 转为前端可正确解析的 ISO 字符串。
    库内为 UTC（无时区或 naive），返回时带 Z 表示 UTC，前端用 formatBeijingTime 转为北京时间展示。
    """
    if dt is None:
        return ""
    if not hasattr(dt, "isoformat"):
        return str(dt)
    s = dt.isoformat()
    if getattr(dt, "tzinfo", None) is None:
        return s + "Z" if not s.endswith("Z") else s
    return s
