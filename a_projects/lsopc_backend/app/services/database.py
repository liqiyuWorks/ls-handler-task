# -*- coding: utf-8 -*-
"""MongoDB 异步连接服务"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    db = None

    async def connect(self):
        """建立 MongoDB 连接"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGO_URL)
            self.db = self.client[settings.MONGO_DB]
            # 简单验证连接，ping 当前数据库而不是 admin，因为权限可能受限
            await self.db.command('ping')
            logger.info("Successfully connected to MongoDB database: %s", settings.MONGO_DB)
        except Exception as e:
            logger.error("Failed to connect to MongoDB: %s", e)
            raise

    async def disconnect(self):
        """关闭 MongoDB 连接"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")


db = Database()
