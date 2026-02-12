# -*- coding: utf-8 -*-
"""Gemini 图片生成服务"""
import logging
import base64
import uuid
import os
import httpx
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from app.config import settings
from app.services.database import db

logger = logging.getLogger(__name__)


@dataclass
class ImageGenerateResult:
    """图片生成结果"""
    image_url: Optional[str] = None
    cost: float = 0.0
    cost_detail: str = ""


class ImageService:
    """Gemini 图片生成服务"""

    def __init__(self):
        self.api_url = settings.GEMINI_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.GEMINI_API_KEY}"
        }
        self.timeout = settings.GEMINI_TIMEOUT

    def _calculate_cost(self, resolution: str, aspect_ratio: str) -> Tuple[float, str]:
        """计算图片生成成本"""
        cost = settings.GEMINI_PRICING.get(resolution, settings.GEMINI_PRICING["1K"])
        detail = f"Gemini 图片生成 (分辨率: {resolution}, 宽高比: {aspect_ratio}) - ${cost:.3f}/张"
        return cost, detail

    async def generate_image(
        self,
        prompt: str,
        username: str,
        aspect_ratio: str = "1:1",
        resolution: str = "2K"
    ) -> ImageGenerateResult:
        """
        使用 Gemini API 生成图片
        
        Args:
            prompt: 图片描述提示词
            username: 用户名
            aspect_ratio: 宽高比 (21:9, 16:9, 4:3, 3:2, 1:1, 9:16, 3:4, 2:3, 5:4, 4:5)
            resolution: 分辨率 (1K, 2K, 4K)
        
        Returns:
            ImageGenerateResult 包含图片URL和成本信息
        """
        # 计算成本
        cost, cost_detail = self._calculate_cost(resolution, aspect_ratio)

        try:
            logger.info(f"[Gemini] 开始生成图片, prompt: {prompt}, resolution: {resolution}, aspect_ratio: {aspect_ratio}")

            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                    "imageConfig": {"aspectRatio": aspect_ratio}
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )

            if response.status_code != 200:
                logger.error(f"[Gemini] API 请求失败, status: {response.status_code}, body: {response.text}")
                raise Exception(f"Gemini API 请求失败，状态码: {response.status_code}")

            result = response.json()

            # 提取图片数据
            try:
                image_data = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                mime_type = result["candidates"][0]["content"]["parts"][0]["inlineData"].get("mimeType", "image/png")
            except (KeyError, IndexError) as e:
                logger.error(f"[Gemini] 响应格式异常: {result}")
                raise Exception(f"Gemini 响应格式异常: {e}") from e

            # 确定文件扩展名
            ext = "png"
            if "jpeg" in mime_type or "jpg" in mime_type:
                ext = "jpg"
            elif "webp" in mime_type:
                ext = "webp"

            # 保存图片到本地
            filename = f"lspic_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join("static", "images", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            decoded_data = base64.b64decode(image_data)
            with open(filepath, "wb") as f:
                f.write(decoded_data)

            image_url = f"/static/images/{filename}"
            logger.info(f"[Gemini] 图片已保存: {image_url}, 消费: ${cost:.3f}")

            # 保存到数据库
            await self._save_history(
                username=username,
                prompt=prompt,
                image_url=image_url,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                cost=cost
            )

            return ImageGenerateResult(
                image_url=image_url,
                cost=cost,
                cost_detail=cost_detail
            )

        except Exception as e:
            logger.error(f"[Gemini] 生成图片失败: {e}")
            raise e

    async def _save_history(
        self,
        username: str,
        prompt: str,
        image_url: str,
        aspect_ratio: str,
        resolution: str,
        cost: float = 0.0
    ):
        """保存生成记录到数据库"""
        try:
            history_record = {
                "username": username,
                "prompt": prompt,
                "image_url": image_url,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "cost": cost,
                "created_at": datetime.utcnow()
            }
            await db.db.image_history.insert_one(history_record)
            logger.info(f"[DB] 图片生成记录已保存, user: {username}, resolution: {resolution}, cost: ${cost:.3f}")
        except Exception as e:
            logger.warning(f"[DB] 保存历史记录失败: {e}")


image_service = ImageService()
