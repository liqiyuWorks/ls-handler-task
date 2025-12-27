#!/usr/bin/env python3
"""
MongoDB存储模块
用于存储FFA格式化后的JSON数据
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MongoDBStorage:
    """MongoDB存储类"""
    
    def __init__(self, config: Dict[str, Any], page_key: str = None):
        """初始化MongoDB连接
        
        Args:
            config: MongoDB配置字典
            page_key: 页面键，用于确定collection名称
        """
        self.config = config
        self.page_key = page_key
        self.client = None
        self.db = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """建立MongoDB连接"""
        try:
            # 构建连接字符串
            if self.config.get('username') and self.config.get('password'):
                connection_string = f"mongodb://{self.config['username']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            else:
                connection_string = f"mongodb://{self.config['host']}:{self.config['port']}"
            
            # 创建客户端
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            
            # 测试连接
            self.client.admin.command('ping')
            
            # 获取数据库和集合
            self.db = self.client[self.config['database']]
            
            # 根据page_key确定collection名称
            if self.page_key:
                collection_name = f"{self.page_key}_data"
            else:
                collection_name = self.config['collection']
            
            self.collection = self.db[collection_name]
            
            # 创建唯一索引
            self._create_indexes()
            
            logger.info(f"✓ MongoDB连接成功: {self.config['host']}:{self.config['port']}")
            logger.info(f"✓ 使用集合: {collection_name}")
            
        except ConnectionFailure as e:
            logger.error(f"✗ MongoDB连接失败: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ MongoDB初始化失败: {e}")
            raise
    
    def _create_indexes(self):
        """创建索引"""
        try:
            # 为swap_date创建唯一索引
            self.collection.create_index("swap_date", unique=True)
            logger.info("✓ 已创建swap_date唯一索引")
            
            # 为timestamp创建索引（用于查询）
            self.collection.create_index("timestamp")
            logger.info("✓ 已创建timestamp索引")
            
        except Exception as e:
            logger.warning(f"创建索引时出现警告: {e}")
    
    def store_ffa_data(self, data: Dict[str, Any]) -> bool:
        """存储FFA数据
        
        Args:
            data: 格式化的FFA数据
            
        Returns:
            bool: 存储是否成功
        """
        try:
            # 支持新的数据格式，从metadata中获取swap_date
            swap_date = data.get("metadata", {}).get("swap_date") or data.get("swap_date")
            if not swap_date:
                logger.error("✗ 数据无效或缺少swap_date字段")
                return False
            
            # 根据页面类型选择存储方法
            if self.page_key == "p4tc_spot_decision":
                return self._store_p4tc_data(data, swap_date)
            else:
                return self._store_ffa_data(data, swap_date)
                
        except Exception as e:
            logger.error(f"✗ 存储数据失败: {e}")
            return False
    
    def _store_ffa_data(self, data: Dict[str, Any], swap_date: str) -> bool:
        """存储FFA数据的内部方法"""
        try:
            # 添加存储时间戳
            data['stored_at'] = datetime.now().isoformat()
            data['_id'] = swap_date  # 使用swap_date作为文档ID
            data['swap_date'] = swap_date  # 确保顶层有swap_date字段
            
            # 尝试插入或更新
            result = self.collection.replace_one(
                {"swap_date": swap_date},
                data,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"✓ FFA数据存储成功: swap_date={swap_date}")
                return True
            else:
                logger.warning(f"⚠ FFA数据未更新: swap_date={swap_date}")
                return True
                
        except DuplicateKeyError:
            logger.warning(f"⚠ 数据已存在，尝试更新: swap_date={swap_date}")
            return self.update_ffa_data(data)
        except Exception as e:
            logger.error(f"✗ 存储FFA数据失败: {e}")
            return False
    
    def _store_p4tc_data(self, data: Dict[str, Any], swap_date: str) -> bool:
        """存储P4TC现货应用决策数据的内部方法"""
        try:
            # 提取核心数据并创建结构化的JSON文档
            core_data = self._extract_p4tc_core_data(data)
            
            # 创建完整的文档结构
            document = {
                "_id": swap_date,
                "swap_date": swap_date,
                "timestamp": data.get("metadata", {}).get("timestamp", ""),
                "stored_at": datetime.now().isoformat(),
                "page_name": "P4TC现货应用决策",
                "data_source": "AquaBridge",
                "version": "1.0",
                "core_data": core_data,
                "raw_data": data  # 保留原始数据作为备份
            }
            
            # 尝试插入或更新
            result = self.collection.replace_one(
                {"swap_date": swap_date},
                document,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.info(f"✓ P4TC数据存储成功: swap_date={swap_date}")
                logger.info(f"✓ 核心数据: 盈亏比={core_data.get('profit_loss_ratio')}, 交易方向={core_data.get('recommended_direction')}")
                return True
            else:
                logger.warning(f"⚠ P4TC数据未更新: swap_date={swap_date}")
                return True
                
        except Exception as e:
            logger.error(f"✗ 存储P4TC数据失败: {e}")
            return False
    
    def _extract_p4tc_core_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取P4TC核心数据"""
        core_data = {
            "trading_recommendation": {
                "profit_loss_ratio": None,
                "recommended_direction": None,
                "direction_confidence": None
            },
            "current_forecast": {
                "date": None,
                "high_expected_value": None,
                "price_difference_ratio": None,
                "price_difference_range": None,
                "forecast_value": None,
                "probability": None
            },
            "statistics": {
                "total_rows": 0,
                "data_quality": "unknown"
            }
        }
        
        # 从contracts中提取数据
        contracts = data.get("contracts", {})
        
        # 提取原始表格数据统计
        raw_table_data = contracts.get("raw_table_data", {})
        core_data["statistics"]["total_rows"] = raw_table_data.get("total_rows", 0)
        core_data["statistics"]["data_quality"] = "high" if core_data["statistics"]["total_rows"] > 0 else "low"
        
        # 提取P4TC分析数据
        p4tc_analysis = contracts.get("p4tc_analysis", {})
        if p4tc_analysis:
            trading_rec = p4tc_analysis.get("trading_recommendation", {})
            current_forecast = p4tc_analysis.get("current_forecast", {})
            
            # 提取交易建议
            core_data["trading_recommendation"]["profit_loss_ratio"] = trading_rec.get("profit_loss_ratio")
            core_data["trading_recommendation"]["recommended_direction"] = trading_rec.get("recommended_direction")
            core_data["trading_recommendation"]["direction_confidence"] = trading_rec.get("direction_confidence")
            
            # 提取当前预测
            core_data["current_forecast"]["date"] = current_forecast.get("date")
            core_data["current_forecast"]["high_expected_value"] = current_forecast.get("high_expected_value")
            core_data["current_forecast"]["price_difference_ratio"] = current_forecast.get("price_difference_ratio")
            core_data["current_forecast"]["price_difference_range"] = current_forecast.get("price_difference_range")
            core_data["current_forecast"]["forecast_value"] = current_forecast.get("forecast_value")
            core_data["current_forecast"]["probability"] = current_forecast.get("probability")
        
        return core_data
    
    def update_ffa_data(self, data: Dict[str, Any]) -> bool:
        """更新FFA数据
        
        Args:
            data: 格式化的FFA数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if not data or 'swap_date' not in data:
                logger.error("✗ 数据无效或缺少swap_date字段")
                return False
            
            # 添加更新时间戳
            data['updated_at'] = datetime.now().isoformat()
            
            result = self.collection.update_one(
                {"swap_date": data['swap_date']},
                {"$set": data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✓ FFA数据更新成功: swap_date={data['swap_date']}")
                return True
            else:
                logger.warning(f"⚠ FFA数据未找到或无需更新: swap_date={data['swap_date']}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 更新FFA数据失败: {e}")
            return False
    
    def get_ffa_data(self, swap_date: str) -> Optional[Dict[str, Any]]:
        """获取FFA数据
        
        Args:
            swap_date: 掉期日期
            
        Returns:
            Dict: FFA数据或None
        """
        try:
            data = self.collection.find_one({"swap_date": swap_date})
            if data:
                # 移除MongoDB的_id字段
                data.pop('_id', None)
                logger.info(f"✓ 获取FFA数据成功: swap_date={swap_date}")
                return data
            else:
                logger.warning(f"⚠ 未找到FFA数据: swap_date={swap_date}")
                return None
                
        except Exception as e:
            logger.error(f"✗ 获取FFA数据失败: {e}")
            return None
    
    def list_ffa_data(self, limit: int = 10) -> list:
        """列出FFA数据
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: FFA数据列表
        """
        try:
            cursor = self.collection.find().sort("timestamp", -1).limit(limit)
            data_list = []
            
            for doc in cursor:
                doc.pop('_id', None)
                data_list.append(doc)
            
            logger.info(f"✓ 获取FFA数据列表成功: 共{len(data_list)}条")
            return data_list
            
        except Exception as e:
            logger.error(f"✗ 获取FFA数据列表失败: {e}")
            return []
    
    def delete_ffa_data(self, swap_date: str) -> bool:
        """删除FFA数据
        
        Args:
            swap_date: 掉期日期
            
        Returns:
            bool: 删除是否成功
        """
        try:
            result = self.collection.delete_one({"swap_date": swap_date})
            
            if result.deleted_count > 0:
                logger.info(f"✓ FFA数据删除成功: swap_date={swap_date}")
                return True
            else:
                logger.warning(f"⚠ 未找到要删除的FFA数据: swap_date={swap_date}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 删除FFA数据失败: {e}")
            return False
    
    def get_p4tc_core_data(self, swap_date: str) -> Optional[Dict[str, Any]]:
        """获取P4TC核心数据
        
        Args:
            swap_date: 掉期日期
            
        Returns:
            Dict: P4TC核心数据或None
        """
        try:
            document = self.collection.find_one({"swap_date": swap_date})
            if document and "core_data" in document:
                core_data = document["core_data"]
                logger.info(f"✓ 获取P4TC核心数据成功: swap_date={swap_date}")
                return core_data
            else:
                logger.warning(f"⚠ 未找到P4TC核心数据: swap_date={swap_date}")
                return None
                
        except Exception as e:
            logger.error(f"✗ 获取P4TC核心数据失败: {e}")
            return None
    
    def list_p4tc_core_data(self, limit: int = 10) -> list:
        """列出P4TC核心数据
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: P4TC核心数据列表
        """
        try:
            cursor = self.collection.find(
                {"core_data": {"$exists": True}},
                {"swap_date": 1, "timestamp": 1, "core_data": 1, "stored_at": 1}
            ).sort("timestamp", -1).limit(limit)
            
            data_list = []
            for doc in cursor:
                data_list.append({
                    "swap_date": doc.get("swap_date"),
                    "timestamp": doc.get("timestamp"),
                    "stored_at": doc.get("stored_at"),
                    "core_data": doc.get("core_data", {})
                })
            
            logger.info(f"✓ 获取P4TC核心数据列表成功: 共{len(data_list)}条")
            return data_list
            
        except Exception as e:
            logger.error(f"✗ 获取P4TC核心数据列表失败: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            collection_name = self.collection.name
            stats = self.db.command("collStats", collection_name)
            return {
                "count": stats.get('count', 0),
                "size": stats.get('size', 0),
                "avgObjSize": stats.get('avgObjSize', 0),
                "storageSize": stats.get('storageSize', 0)
            }
        except Exception as e:
            logger.error(f"✗ 获取统计信息失败: {e}")
            return {}
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB连接已关闭")


def load_config(config_file: str = "mongodb_config.json") -> Dict[str, Any]:
    """加载MongoDB配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        Dict: 配置字典
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('mongodb', {})
    except FileNotFoundError:
        logger.warning(f"配置文件不存在: {config_file}，使用默认配置")
        return {
            "enabled": True,
            "host": "153.35.13.226",
            "port": 27017,
            "database": "aquabridge",
            "username": "aquabridge",
            "password": "Aquabridge#2025",
            "collection": "wechat_messages"
        }
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return {}


def main():
    """主函数 - 测试MongoDB连接"""
    import sys
    
    # 加载配置
    config = load_config()
    
    if not config.get('enabled', False):
        print("MongoDB存储已禁用")
        return
    
    try:
        # 创建存储实例
        storage = MongoDBStorage(config)
        
        # 测试连接
        print("=== MongoDB连接测试 ===")
        print(f"主机: {config['host']}:{config['port']}")
        print(f"数据库: {config['database']}")
        print(f"集合: {config['collection']}")
        
        # 获取统计信息
        stats = storage.get_collection_stats()
        print(f"\n=== 集合统计 ===")
        print(f"文档数量: {stats.get('count', 0)}")
        print(f"集合大小: {stats.get('size', 0)} bytes")
        print(f"平均文档大小: {stats.get('avgObjSize', 0)} bytes")
        
        # 列出最近的数据
        recent_data = storage.list_ffa_data(limit=5)
        print(f"\n=== 最近5条数据 ===")
        for i, data in enumerate(recent_data, 1):
            print(f"{i}. swap_date: {data.get('swap_date', 'N/A')}, timestamp: {data.get('timestamp', 'N/A')}")
        
        storage.close()
        print("\n✓ MongoDB测试完成")
        
    except Exception as e:
        print(f"✗ MongoDB测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
