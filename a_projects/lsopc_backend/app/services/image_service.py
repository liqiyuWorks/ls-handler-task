# -*- coding: utf-8 -*-
"""Gemini 图片生成服务：成本价(api_price)与平台定价(lsopc_price)分离，价格从 models_price_map 动态读取"""
import logging
import base64
import uuid
import os
import httpx
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.config import settings
from app.services.database import db
from app.services.billing_utils import get_model_price_map, deduct_and_record, ModelPriceMap

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

    async def _get_price_map_for_generate(self) -> ModelPriceMap:
        """获取当前图片模型的价格配置，无表记录时使用 config 兜底"""
        price_map = await get_model_price_map(settings.GEMINI_IMAGE_MODEL)
        if price_map:
            return price_map
        default_usd = float(settings.GEMINI_PRICING.get("2K", 0.05))
        return ModelPriceMap(
            model=settings.GEMINI_IMAGE_MODEL,
            api_price=default_usd,
            lsopc_price=default_usd,
            exchange_rate=settings.USD_TO_CNY,
            remarks="(config 兜底)",
        )

    async def _deduct_and_record_spent(self, username: str, cost_cny: float) -> None:
        """原子扣款并写入图片生成调用记录"""
        await deduct_and_record(username, cost_cny, record_type="image", type_label="图片生成")

    async def generate_image(
        self,
        prompt: str,
        username: str,
        aspect_ratio: str = "1:1",
        resolution: str = "2K",
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = "image/png",
    ) -> ImageGenerateResult:
        """
        使用 Gemini API 生成或编辑图片。
        无参考图：文生图；有参考图：图片编辑/PS 模式 (generateContent 图+文)。
        价格从 models_price_map 动态读取。
        """
        # 动态价格配置（表优先，无则 config 兜底）
        price_map = await self._get_price_map_for_generate()
        cost_usd = price_map.lsopc_price
        cost_cny = price_map.cost_cny()
        cost_detail = f"平台定价 ${cost_usd:.3f}/张 (约 {cost_cny:.2f} 元)"

        try:
            mode = "图片编辑/PS" if image_base64 else "文生图"
            logger.info(
                "[Gemini] 开始 %s, prompt=%s, resolution=%s, aspect_ratio=%s, 扣款=%.2f 元",
                mode, prompt, resolution, aspect_ratio, cost_cny,
            )

            parts = [{"text": prompt}]
            if image_base64:
                mime = (image_mime_type or "image/png").strip()
                if mime not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
                    mime = "image/png"
                parts.append({"inline_data": {"mime_type": mime, "data": image_base64}})

            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                    "imageConfig": {
                        "aspectRatio": aspect_ratio,
                        "imageSize": resolution
                    }
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
            logger.info("[Gemini] 图片已保存: %s, 扣款: %.2f 元 (平台价 $%.3f)", image_url, cost_cny, cost_usd)

            # 原子扣款并更新累计消费（与用户表一致）
            await self._deduct_and_record_spent(username, cost_cny)

            # 保存生成记录到历史（记录平台定价 USD）
            await self._save_history(
                username=username,
                prompt=prompt,
                image_url=image_url,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                cost=cost_usd,
            )

            return ImageGenerateResult(
                image_url=image_url,
                cost=cost_usd,
                cost_detail=cost_detail,
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
