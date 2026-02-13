# -*- coding: utf-8 -*-
"""Gemini 图片生成服务：成本价(api_price)与平台定价(lsopc_price)分离，价格从 models_price_map 动态读取"""
import logging
import base64
import uuid
import os
import httpx
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pymongo import ReturnDocument

from app.config import settings
from app.services.database import db

logger = logging.getLogger(__name__)

# 集合名：模型价格映射（成本价、平台价、汇率）
MODELS_PRICE_MAP_COLLECTION = "models_price_map"
# 调用记录集合（个人中心「调用记录」展示）
USAGE_RECORDS_COLLECTION = "usage_records"


@dataclass
class ModelPriceMap:
    """models_price_map 表一行：第三方成本价 vs 平台定价，及汇率"""
    model: str
    api_price: float   # 成本价 USD/张
    lsopc_price: float # 平台定价 USD/张，向用户收取
    exchange_rate: float  # 美元对人民币汇率
    remarks: str = ""

    def cost_cny_per_image(self) -> float:
        """每张图片扣款金额（元），保留两位小数"""
        return round(float(Decimal(str(self.lsopc_price)) * Decimal(str(self.exchange_rate))), 2)


@dataclass
class ImageGenerateResult:
    """图片生成结果"""
    image_url: Optional[str] = None
    cost: float = 0.0
    cost_detail: str = ""


async def get_model_price_map(model_name: str) -> Optional[ModelPriceMap]:
    """
    从 MongoDB models_price_map 按 model 查询价格配置。
    表字段：model, api_price, lsopc_price（或 lsopc_proce 兼容拼写）, exchange_rate, remarks
    """
    doc = await db.db[MODELS_PRICE_MAP_COLLECTION].find_one({"model": model_name})
    if not doc:
        return None
    api_price = _parse_decimal(doc.get("api_price"), 0.05)
    # 兼容字段拼写 lsopc_proce
    lsopc_price = _parse_decimal(doc.get("lsopc_price") or doc.get("lsopc_proce"), api_price)
    exchange_rate = _parse_decimal(doc.get("exchange_rate"), settings.USD_TO_CNY)
    return ModelPriceMap(
        model=doc.get("model", model_name),
        api_price=api_price,
        lsopc_price=lsopc_price,
        exchange_rate=exchange_rate,
        remarks=doc.get("remarks", ""),
    )


def _parse_decimal(value, default: float) -> float:
    """将字符串或数字转为 float，失败返回 default"""
    if value is None:
        return default
    try:
        return float(Decimal(str(value).strip()))
    except Exception:
        return default


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
        """
        原子扣款并更新累计消费：balance 减少、total_spent 增加，保证一致性。
        cost_cny：本次扣款金额（元）。若余额不足则抛出异常。
        """
        if cost_cny <= 0:
            return
        updated = await db.db.users.find_one_and_update(
            {"username": username, "balance": {"$gte": cost_cny}},
            {"$inc": {"balance": -cost_cny, "total_spent": cost_cny}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise ValueError("余额不足，请充值后重试")
        logger.info(
            "[DB] 扣款成功 user=%s cost_cny=%.2f balance_after=%.2f total_spent=%.2f",
            username, cost_cny, updated.get("balance", 0), updated.get("total_spent", 0),
        )
        # 写入调用记录，供个人中心「调用记录」展示
        try:
            await db.db[USAGE_RECORDS_COLLECTION].insert_one({
                "username": username,
                "record_type": "image",
                "type_label": "图片生成",
                "amount": cost_cny,
                "count": 1,
                "created_at": datetime.utcnow(),
            })
        except Exception as e:
            logger.warning("[DB] 写入 usage_records 失败: %s", e)

    async def generate_image(
        self,
        prompt: str,
        username: str,
        aspect_ratio: str = "1:1",
        resolution: str = "2K"
    ) -> ImageGenerateResult:
        """
        使用 Gemini API 生成图片。
        价格从 models_price_map 动态读取：平台按 lsopc_price(USD) 向用户收费，按 exchange_rate 折算为元扣款。
        """
        # 动态价格配置（表优先，无则 config 兜底）
        price_map = await self._get_price_map_for_generate()
        cost_usd = price_map.lsopc_price
        cost_cny = price_map.cost_cny_per_image()
        cost_detail = f"平台定价 ${cost_usd:.3f}/张 (约 {cost_cny:.2f} 元)"

        try:
            logger.info(
                "[Gemini] 开始生成图片, prompt=%s, resolution=%s, aspect_ratio=%s, 扣款=%.2f 元",
                prompt, resolution, aspect_ratio, cost_cny,
            )

            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
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
