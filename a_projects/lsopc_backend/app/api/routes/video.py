# -*- coding: utf-8 -*-
"""VEO 视频生成接口：文生视频、单帧图生视频、多帧图生视频（接入计费）"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config import settings
from app.schemas.auth import UserBase
from app.api.routes.auth import get_current_user
from app.schemas.video import (
    CreateVideoTextRequest,
    CreateVideoResponse,
    VideoStatusResponse,
    VideoContentResponse,
    VideoHistoryItem,
    PROMPT_SUMMARY_MAX,
)
from app.services.veo_service import veo_client
from app.services.billing_utils import get_model_price_map, deduct_and_record
from app.services.database import db
from app.utils.time_utils import utc_iso_for_api

router = APIRouter()
logger = logging.getLogger(__name__)

# 文生视频模型（无 -fl）
TEXT_MODELS = ["veo-3.1", "veo-3.1-fast", "veo-3.1-landscape", "veo-3.1-landscape-fast"]
# 图生视频模型（首尾帧 -fl）
IMAGE_MODELS = ["veo-3.1-fl", "veo-3.1-fast-fl", "veo-3.1-landscape-fl", "veo-3.1-landscape-fast-fl"]
IMAGE_MODEL_DEFAULT = "veo-3.1-landscape-fl"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

VIDEO_TASKS_COLLECTION = "video_tasks"


def _check_api_key() -> None:
    if not veo_client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="视频生成服务未配置 API 密钥，请在 .env 中配置 GEMINI_API_KEY",
        )


async def _check_balance_and_get_price(username: str, model: str) -> float:
    """检查余额并返回该模型平台价（元）。不足则抛 HTTPException"""
    price_map = await get_model_price_map(model)
    if not price_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"模型 {model} 未在 models_price_map 中配置价格，请联系管理员",
        )
    cost_cny = price_map.cost_cny()
    user = await db.db.users.find_one({"username": username})
    balance = float(user.get("balance", 0))
    if balance < cost_cny:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"余额不足，当前余额 ¥{balance:.2f}，需要 ¥{cost_cny:.2f}",
        )
    return cost_cny


async def _store_video_task(
    video_id: str, username: str, model: str, prompt: str | None = None
) -> None:
    """存储视频任务，供 get_content 扣款及历史记录展示"""
    await db.db[VIDEO_TASKS_COLLECTION].insert_one({
        "video_id": video_id,
        "username": username,
        "model": model,
        "prompt": (prompt or "").strip() or None,
        "created_at": datetime.utcnow(),
        "charged": False,
    })


async def _charge_if_needed(video_id: str, username: str) -> None:
    """若未扣款则扣款并写入调用记录"""
    task = await db.db[VIDEO_TASKS_COLLECTION].find_one({
        "video_id": video_id,
        "username": username,
    })
    if not task or task.get("charged"):
        return
    model = task.get("model", "veo-3.1")
    price_map = await get_model_price_map(model)
    if not price_map:
        logger.warning("[Video] 模型 %s 无价格配置，跳过扣款", model)
        return
    cost_cny = price_map.cost_cny()
    if cost_cny <= 0:
        return
    await deduct_and_record(username, cost_cny, record_type="video", type_label="视频生成")
    await db.db[VIDEO_TASKS_COLLECTION].update_one(
        {"video_id": video_id, "username": username},
        {"$set": {"charged": True}},
    )
    logger.info("[Video] 扣款成功 video_id=%s user=%s cost_cny=%.2f", video_id, username, cost_cny)


@router.post("/create/text", response_model=CreateVideoResponse)
async def create_video_text(
    body: CreateVideoTextRequest,
    current_user: UserBase = Depends(get_current_user),
):
    """文生视频：根据文字描述生成视频（计费）"""
    _check_api_key()
    model = body.model if body.model in TEXT_MODELS else "veo-3.1"
    await _check_balance_and_get_price(current_user.username, model)
    try:
        video_id = await veo_client.create_video_text(prompt=body.prompt, model=model)
        await _store_video_task(video_id, current_user.username, model, prompt=body.prompt)
        return CreateVideoResponse(video_id=video_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[API] 文生视频创建失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create/image", response_model=CreateVideoResponse)
async def create_video_single_image(
    prompt: str = Form(..., min_length=1),
    model: str = Form(default=IMAGE_MODEL_DEFAULT),
    input_reference: UploadFile = File(...),
    current_user: UserBase = Depends(get_current_user),
):
    """单帧图生视频：以一张图片作为首帧（计费）"""
    _check_api_key()
    model = model if model in IMAGE_MODELS else IMAGE_MODEL_DEFAULT
    content = await input_reference.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")
    mime = input_reference.content_type or "image/jpeg"
    if mime not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPEG、PNG、WebP 格式")
    ext = "jpg" if "jpeg" in mime or "jpg" in mime else "png" if "png" in mime else "webp"
    filename = input_reference.filename or f"image.{ext}"
    await _check_balance_and_get_price(current_user.username, model)
    try:
        video_id = await veo_client.create_video_single_image(
            prompt=prompt,
            image_bytes=content,
            filename=filename,
            mime_type=mime,
            model=model,
        )
        await _store_video_task(video_id, current_user.username, model, prompt=prompt)
        return CreateVideoResponse(video_id=video_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[API] 单帧图生视频创建失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create/images", response_model=CreateVideoResponse)
async def create_video_dual_images(
    prompt: str = Form(..., min_length=1),
    model: str = Form(default=IMAGE_MODEL_DEFAULT),
    image_first: UploadFile = File(..., alias="image_first"),
    image_last: UploadFile = File(..., alias="image_last"),
    current_user: UserBase = Depends(get_current_user),
):
    """多帧图生视频：首尾双图（计费）"""
    _check_api_key()
    model = model if model in IMAGE_MODELS else IMAGE_MODEL_DEFAULT
    first_content = await image_first.read()
    last_content = await image_last.read()
    if len(first_content) > MAX_IMAGE_SIZE or len(last_content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="单张图片大小不能超过 10MB")
    mime1 = image_first.content_type or "image/jpeg"
    mime2 = image_last.content_type or "image/jpeg"
    if mime1 not in ALLOWED_IMAGE_TYPES or mime2 not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPEG、PNG、WebP 格式")
    ext1 = "jpg" if "jpeg" in mime1 or "jpg" in mime1 else "png" if "png" in mime1 else "webp"
    ext2 = "jpg" if "jpeg" in mime2 or "jpg" in mime2 else "png" if "png" in mime2 else "webp"
    fn1 = image_first.filename or f"first.{ext1}"
    fn2 = image_last.filename or f"last.{ext2}"
    await _check_balance_and_get_price(current_user.username, model)
    try:
        video_id = await veo_client.create_video_dual_images(
            prompt=prompt,
            image_first_bytes=first_content,
            image_last_bytes=last_content,
            filename_first=fn1,
            filename_last=fn2,
            mime_type=mime1,
            model=model,
        )
        await _store_video_task(video_id, current_user.username, model, prompt=prompt)
        return CreateVideoResponse(video_id=video_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[API] 多帧图生视频创建失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: str,
    current_user: UserBase = Depends(get_current_user),
):
    """查询视频任务状态"""
    _check_api_key()
    try:
        data = await veo_client.get_status(video_id)
        status_val = data.get("status", "unknown")
        return VideoStatusResponse(
            video_id=video_id,
            status=status_val,
            detail=data.get("detail") or data.get("message"),
        )
    except Exception as e:
        logger.exception("[API] 查询视频状态失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _absolute_video_url(url: str | None) -> str | None:
    """将相对路径转为可预览的完整 URL（测试 localhost:8000，部署 api.lsopc.cn）"""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = (settings.PUBLIC_BASE_URL or "http://localhost:8000").rstrip("/")
    return f"{base}{url}" if url.startswith("/") else f"{base}/{url}"


@router.get("/content/{video_id}", response_model=VideoContentResponse)
async def get_video_content(
    video_id: str,
    current_user: UserBase = Depends(get_current_user),
):
    """获取视频内容（含可直接预览的完整 URL）。首次成功获取时扣款并写入调用记录"""
    _check_api_key()
    try:
        data = await veo_client.get_content(video_id)
        await _charge_if_needed(video_id, current_user.username)
        rel_url = data.get("url")
        url = _absolute_video_url(rel_url)
        if rel_url:
            await db.db[VIDEO_TASKS_COLLECTION].update_one(
                {"video_id": video_id, "username": current_user.username},
                {"$set": {"video_url": rel_url}},
            )
        return VideoContentResponse(
            video_id=video_id,
            url=url,
            resolution=data.get("resolution"),
        )
    except Exception as e:
        logger.exception("[API] 获取视频内容失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[VideoHistoryItem])
async def get_video_history(
    limit: int = 5,
    current_user: UserBase = Depends(get_current_user),
):
    """获取当前用户最近 N 条视频生成记录（默认 5 条）"""
    limit = min(max(1, limit), 20)
    cursor = db.db[VIDEO_TASKS_COLLECTION].find(
        {"username": current_user.username}
    ).sort("created_at", -1).limit(limit)
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
        items.append(VideoHistoryItem(
            video_id=doc["video_id"],
            model=doc.get("model", ""),
            created_at=created_at,
            video_url=_absolute_video_url(doc.get("video_url")),
            prompt_summary=prompt_summary,
        ))
    return items


@router.get("/options")
async def get_video_options():
    """获取视频生成支持的选项（含 models_price_map 动态定价）"""
    text_models_with_price = []
    for m in TEXT_MODELS:
        pm = await get_model_price_map(m)
        text_models_with_price.append({
            "model": m,
            "price_usd": pm.lsopc_price if pm else 0.25,
            "price_cny": pm.cost_cny() if pm else 1.80,
        })
    image_models_with_price = []
    for m in IMAGE_MODELS:
        pm = await get_model_price_map(m)
        image_models_with_price.append({
            "model": m,
            "price_usd": pm.lsopc_price if pm else 0.25,
            "price_cny": pm.cost_cny() if pm else 1.80,
        })
    return {
        "text_models": TEXT_MODELS,
        "text_models_with_price": text_models_with_price,
        "text_model_default": "veo-3.1",
        "image_models": IMAGE_MODELS,
        "image_models_with_price": image_models_with_price,
        "image_model_default": IMAGE_MODEL_DEFAULT,
        "supported_image_types": list(ALLOWED_IMAGE_TYPES),
        "max_image_size_mb": MAX_IMAGE_SIZE // (1024 * 1024),
    }
