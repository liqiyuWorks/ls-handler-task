# -*- coding: utf-8 -*-
"""视频生成相关 Pydantic 模型"""

from typing import Optional

from pydantic import BaseModel, Field


class CreateVideoTextRequest(BaseModel):
    """文生视频请求"""
    prompt: str = Field(..., min_length=1, description="视频描述")
    model: str = Field(default="veo-3.1", description="模型: veo-3.1 | veo-3.1-fast")


class CreateVideoResponse(BaseModel):
    """创建视频任务响应"""
    video_id: str = Field(..., description="任务 ID")


class VideoStatusResponse(BaseModel):
    """任务状态响应"""
    video_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="pending | processing | completed | failed")
    detail: Optional[str] = Field(default=None, description="状态详情")


class VideoContentResponse(BaseModel):
    """视频内容响应"""
    video_id: str = Field(..., description="任务 ID")
    url: Optional[str] = Field(default=None, description="视频 URL")
    resolution: Optional[str] = Field(default=None, description="分辨率")


# 历史记录中提示词概要最大长度（字符数，超出则截断并加省略号）
PROMPT_SUMMARY_MAX = 24


class VideoHistoryItem(BaseModel):
    """历史视频记录（最近 N 条）"""
    video_id: str = Field(..., description="任务 ID")
    model: str = Field(..., description="模型名")
    created_at: str = Field(..., description="创建时间 ISO 字符串")
    video_url: Optional[str] = Field(default=None, description="视频可预览完整 URL，未拉取过则为空")
    prompt_summary: Optional[str] = Field(default=None, description="提示词概要，便于识别当次生成内容")
