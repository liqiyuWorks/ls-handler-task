# -*- coding: utf-8 -*-
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

# 支持的宽高比
SUPPORTED_ASPECT_RATIOS = [
    "21:9", "16:9", "4:3", "3:2", "1:1",
    "9:16", "3:4", "2:3", "5:4", "4:5"
]

# 支持的分辨率
SUPPORTED_RESOLUTIONS = ["1K", "2K", "4K"]

# 分辨率类型
Resolution = Literal["1K", "2K", "4K"]


class ImageGenerateRequest(BaseModel):
    """图片生成请求 (Gemini)"""
    prompt: str = Field(..., description="图片生成提示词")
    aspect_ratio: Optional[str] = Field("1:1", description="宽高比: 21:9, 16:9, 4:3, 3:2, 1:1, 9:16, 3:4, 2:3, 5:4, 4:5")
    resolution: Resolution = Field("2K", description="分辨率: 1K, 2K, 4K")

    @field_validator('aspect_ratio')
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        if v and v not in SUPPORTED_ASPECT_RATIOS:
            raise ValueError(f"不支持的宽高比 '{v}'，支持的值: {', '.join(SUPPORTED_ASPECT_RATIOS)}")
        return v

    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in SUPPORTED_RESOLUTIONS:
            raise ValueError(f"不支持的分辨率 '{v}'，支持的值: {', '.join(SUPPORTED_RESOLUTIONS)}")
        return v_upper


class ImageGenerateResponse(BaseModel):
    """图片生成响应"""
    status: str
    image_url: Optional[str] = None
    message: Optional[str] = None
    cost: Optional[float] = Field(None, description="本次生成消耗金额 (美元 USD)")
    cost_detail: Optional[str] = Field(None, description="费用详情说明")
