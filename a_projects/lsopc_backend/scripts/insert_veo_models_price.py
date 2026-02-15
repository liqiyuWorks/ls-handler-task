# -*- coding: utf-8 -*-
"""
向 MongoDB models_price_map 插入 VEO 3.1 视频模型定价。
api_price：成本价（USD），图一成本价
lsopc_price：平台价（USD），略高于成本价
exchange_rate：美元对人民币汇率
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# 配置（可从环境变量读取）
MONGO_URL = "mongodb://lsopc:Lsopc%230817@153.35.13.226:27017/lsopc"
COLLECTION = "models_price_map"
EXCHANGE_RATE = 7.1

# VEO 模型定价：api_price 成本价，lsopc_price 平台价（略高）
VEO_MODELS = [
    {"model": "veo-3.1", "api_price": 0.25, "lsopc_price": 0.28, "remarks": "默认竖屏 720x1280"},
    {"model": "veo-3.1-fl", "api_price": 0.25, "lsopc_price": 0.28, "remarks": "竖屏+首尾帧转视频"},
    {"model": "veo-3.1-fast", "api_price": 0.15, "lsopc_price": 0.18, "remarks": "竖屏+快速"},
    {"model": "veo-3.1-fast-fl", "api_price": 0.15, "lsopc_price": 0.18, "remarks": "竖屏+快速+首尾帧"},
    {"model": "veo-3.1-landscape", "api_price": 0.25, "lsopc_price": 0.28, "remarks": "横屏 1280x720"},
    {"model": "veo-3.1-landscape-fl", "api_price": 0.25, "lsopc_price": 0.28, "remarks": "横屏+首尾帧转视频"},
    {"model": "veo-3.1-landscape-fast", "api_price": 0.15, "lsopc_price": 0.18, "remarks": "横屏+快速"},
    {"model": "veo-3.1-landscape-fast-fl", "api_price": 0.15, "lsopc_price": 0.18, "remarks": "横屏+快速+首尾帧"},
]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database(MONGO_URL.split("/")[-1].split("?")[0] or "lsopc")
    col = db[COLLECTION]

    for m in VEO_MODELS:
        doc = {
            "model": m["model"],
            "api_price": m["api_price"],
            "lsopc_price": m["lsopc_price"],
            "exchange_rate": EXCHANGE_RATE,
            "remarks": m["remarks"],
        }
        result = await col.update_one(
            {"model": m["model"]},
            {"$set": doc},
            upsert=True,
        )
        action = "upserted" if result.upserted_id else "updated"
        print(f"{action} {m['model']} api={m['api_price']} lsopc={m['lsopc_price']}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
