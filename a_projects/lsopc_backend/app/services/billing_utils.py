# -*- coding: utf-8 -*-
"""计费工具：从 models_price_map 动态读取价格，扣款并写入调用记录"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pymongo import ReturnDocument

from app.config import settings
from app.services.database import db

logger = logging.getLogger(__name__)

MODELS_PRICE_MAP_COLLECTION = "models_price_map"
USAGE_RECORDS_COLLECTION = "usage_records"


@dataclass
class ModelPriceMap:
    """models_price_map 表一行：api_price 成本价 vs lsopc_price 平台定价（可略高）"""
    model: str
    api_price: float   # 成本价 USD
    lsopc_price: float # 平台定价 USD，向用户收取
    exchange_rate: float
    remarks: str = ""

    def cost_cny(self) -> float:
        """平台定价折算为人民币（元），保留两位小数"""
        return round(float(Decimal(str(self.lsopc_price)) * Decimal(str(self.exchange_rate))), 2)


def parse_decimal(value, default: float) -> float:
    """将字符串或数字转为 float"""
    if value is None:
        return default
    try:
        return float(Decimal(str(value).strip()))
    except Exception:
        return default


async def get_model_price_map(model_name: str) -> Optional[ModelPriceMap]:
    """
    从 MongoDB models_price_map 按 model 查询价格。
    表字段：model, api_price（成本价）, lsopc_price 或 lsopc_proce（平台价，可略高）, exchange_rate, remarks
    """
    doc = await db.db[MODELS_PRICE_MAP_COLLECTION].find_one({"model": model_name})
    if not doc:
        return None
    api_price = parse_decimal(doc.get("api_price"), 0.25)
    lsopc_price = parse_decimal(doc.get("lsopc_price") or doc.get("lsopc_proce"), api_price)
    exchange_rate = parse_decimal(doc.get("exchange_rate"), settings.USD_TO_CNY)
    return ModelPriceMap(
        model=doc.get("model", model_name),
        api_price=api_price,
        lsopc_price=lsopc_price,
        exchange_rate=exchange_rate,
        remarks=doc.get("remarks", ""),
    )


async def deduct_and_record(
    username: str,
    cost_cny: float,
    record_type: str = "image",
    type_label: str = "图片生成",
) -> None:
    """
    原子扣款并写入调用记录。balance 减少、total_spent 增加、usage_records 插入。
    """
    if cost_cny <= 0:
        return
    updated = await db.db.users.find_one_and_update(
        {"$or": [{"username": username}, {"phone": username}], "balance": {"$gte": cost_cny}},
        {"$inc": {"balance": -cost_cny, "total_spent": cost_cny}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise ValueError("余额不足，请充值后重试")
    logger.info(
        "[DB] 扣款成功 user=%s cost_cny=%.2f balance_after=%.2f total_spent=%.2f",
        username, cost_cny, updated.get("balance", 0), updated.get("total_spent", 0),
    )
    try:
        record_doc = {
            "username": username,
            "record_type": record_type,
            "type_label": type_label,
            "amount": cost_cny,
            "count": 1,
            "created_at": datetime.utcnow(),
        }
        if updated.get("phone"):
            record_doc["phone"] = updated["phone"]
        await db.db[USAGE_RECORDS_COLLECTION].insert_one(record_doc)
    except Exception as e:
        logger.warning("[DB] 写入 usage_records 失败: %s", e)
