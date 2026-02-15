# -*- coding: utf-8 -*-
"""Gemini 图片生成接口"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, status

from app.config import settings
from app.schemas.auth import UserBase
from app.schemas.image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageHistoryItem,
    PROMPT_SUMMARY_MAX,
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_RESOLUTIONS,
)
from app.api.routes.auth import get_current_user
from app.services.image_service import image_service
from app.services.database import db
from app.utils.time_utils import utc_iso_for_api

router = APIRouter()
logger = logging.getLogger(__name__)

IMAGE_HISTORY_COLLECTION = "image_history"


def _absolute_image_url(url: str | None) -> str | None:
    """将相对路径转为可预览的完整 URL（与视频一致：测试 localhost，部署 api.lsopc.cn）"""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = (settings.PUBLIC_BASE_URL or "http://localhost:8000").rstrip("/")
    return f"{base}{url}" if url.startswith("/") else f"{base}/{url}"


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
    # 余额校验：须大于 1 元才可生成（能执行到此处说明已登录）
    balance = getattr(current_user, "balance", 0) or 0
    if balance <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请充值后重试",
        )

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
        err_msg = str(e)
        if "余额不足" in err_msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)
        logger.warning(f"[API] 参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as e:
        logger.error(f"[API] 图片生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[ImageHistoryItem])
async def get_image_history(
    limit: int = 5,
    current_user: UserBase = Depends(get_current_user),
):
    """获取当前用户最近 N 条图片生成记录（默认 5 条）"""
    limit = min(max(1, limit), 20)
    cursor = (
        db.db[IMAGE_HISTORY_COLLECTION]
        .find({"username": current_user.username})
        .sort("created_at", -1)
        .limit(limit)
    )
    items = []
    async for doc in cursor:
        created_at = utc_iso_for_api(doc.get("created_at"))
        prompt = (doc.get("prompt") or "").strip()
        if not prompt:
            prompt_summary = None
        elif len(prompt) > PROMPT_SUMMARY_MAX:
            prompt_summary = prompt[:PROMPT_SUMMARY_MAX].rstrip() + "…"
        else:
            prompt_summary = prompt
        items.append(
            ImageHistoryItem(
                id=str(doc.get("_id", "")),
                prompt_summary=prompt_summary,
                created_at=created_at,
                image_url=_absolute_image_url(doc.get("image_url")),
                resolution=doc.get("resolution", "2K"),
                aspect_ratio=doc.get("aspect_ratio", "1:1"),
            )
        )
    return items


@router.get("/options")
async def get_image_options():
    """
    获取图片生成支持的选项及当前动态定价（来自 models_price_map）
    """
    from app.config import settings
    from app.services.image_service import get_model_price_map

    price_map = await get_model_price_map(settings.GEMINI_IMAGE_MODEL)
    if price_map:
        pricing_usd = f"${price_map.lsopc_price:.3f}/张"
        pricing_cny = f"约 {price_map.cost_cny():.2f} 元/张"
        exchange_rate = price_map.exchange_rate
    else:
        pricing_usd = "$0.050/张"
        pricing_cny = "约 0.36 元/张"
        exchange_rate = 7.2

    return {
        "resolutions": {
            "options": SUPPORTED_RESOLUTIONS,
            "default": "2K",
        },
        "aspect_ratios": {
            "options": SUPPORTED_ASPECT_RATIOS,
            "default": "1:1",
        },
        "pricing": {
            "usd_per_image": pricing_usd,
            "cny_per_image": pricing_cny,
            "exchange_rate": exchange_rate,
        },
    }
