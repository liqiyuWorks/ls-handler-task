# -*- coding: utf-8 -*-
"""Gemini 图片生成接口"""
from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.image import ImageGenerateRequest, ImageGenerateResponse, SUPPORTED_ASPECT_RATIOS, SUPPORTED_RESOLUTIONS
from app.schemas.auth import UserBase
from app.api.routes.auth import get_current_user
from app.services.image_service import image_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(
    request_data: ImageGenerateRequest, 
    request: Request,
    current_user: UserBase = Depends(get_current_user)
):
    """
    Gemini 图片生成接口
    
    参数:
    - **prompt**: 图片生成提示词
    - **resolution**: 分辨率 (可选，默认 2K)
      - 支持: 1K, 2K, 4K (均 $0.050/张)
    - **aspect_ratio**: 宽高比 (可选，默认 1:1)
      - 支持: 21:9, 16:9, 4:3, 3:2, 1:1, 9:16, 3:4, 2:3, 5:4, 4:5
    
    响应:
    - **image_url**: 生成的图片地址
    - **cost**: 本次消耗金额 (美元 USD)
    - **cost_detail**: 费用详情说明
    """
    try:
        logger.info(f"[API] 收到图片生成请求, user: {current_user.username}, resolution: {request_data.resolution}, aspect_ratio: {request_data.aspect_ratio}")

        result = await image_service.generate_image(
            prompt=request_data.prompt,
            username=current_user.username,
            aspect_ratio=request_data.aspect_ratio,
            resolution=request_data.resolution
        )
        
        # 构建完整 URL
        full_url = None
        if result.image_url:
            full_url = f"{str(request.base_url).rstrip('/')}{result.image_url}"

        logger.info(f"[API] 图片生成成功, user: {current_user.username}, cost: ${result.cost:.3f}")

        return ImageGenerateResponse(
            status="success",
            image_url=full_url,
            cost=result.cost,
            cost_detail=result.cost_detail
        )

    except ValueError as e:
        logger.warning(f"[API] 参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] 图片生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options")
async def get_image_options():
    """
    获取图片生成支持的选项
    """
    return {
        "resolutions": {
            "options": SUPPORTED_RESOLUTIONS,
            "default": "2K",
            "pricing": "$0.050/张"
        },
        "aspect_ratios": {
            "options": SUPPORTED_ASPECT_RATIOS,
            "default": "1:1"
        }
    }
