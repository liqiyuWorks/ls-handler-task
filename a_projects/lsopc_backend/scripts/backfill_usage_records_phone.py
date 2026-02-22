# -*- coding: utf-8 -*-
"""
为 usage_records 历史数据补全手机号（phone）。
对每条缺少 phone 的记录，按 username 在 users 中查找对应用户的 phone 并回填。
运行方式（在 lsopc_backend 目录下）:
  python -m scripts.backfill_usage_records_phone
或:
  PYTHONPATH=. python scripts/backfill_usage_records_phone.py
"""
import asyncio
import sys

# 允许以脚本方式运行时找到 app
if __name__ == "__main__" and "." not in __name__:
    sys.path.insert(0, ".")


async def run_backfill():
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings

    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB]
    users = db.users
    usage_records = db["usage_records"]

    cursor = usage_records.find({"$or": [{"phone": {"$exists": False}}, {"phone": None}, {"phone": ""}]})
    updated = 0
    skipped = 0
    async for doc in cursor:
        username = doc.get("username")
        if not username:
            skipped += 1
            continue
        user = await users.find_one({"$or": [{"username": username}, {"phone": username}]})
        if not user or not user.get("phone"):
            skipped += 1
            continue
        result = await usage_records.update_one(
            {"_id": doc["_id"]},
            {"$set": {"phone": user["phone"]}},
        )
        if result.modified_count:
            updated += 1
            print(f"  _id={doc['_id']} username={username} -> phone={user['phone']}")

    client.close()
    print(f"回填完成: 更新 {updated} 条, 跳过 {skipped} 条（无对应用户或用户无手机号）")
    return updated


def main():
    asyncio.run(run_backfill())


if __name__ == "__main__":
    main()
