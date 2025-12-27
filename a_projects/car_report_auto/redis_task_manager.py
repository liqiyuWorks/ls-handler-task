#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis任务管理器
"""

import redis
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger
import os


# export REDIS_HOST=153.35.13.226
# export REDIS_PORT=6379
# export REDIS_PASSWORD=5S4Zt7wCCktYJnpAQPHZ
# export SELECTED_DIRECTORY=navgreen

REDIS_HOST = os.getenv('REDIS_HOST', '153.35.13.226')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', "5S4Zt7wCCktYJnpAQPHZ")
REDIS_DB = os.getenv('REDIS_DB', 1)


class RedisTaskManager:
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD):
        self.redis_client = redis.Redis(
            host=host, port=port, db=db, password=password, decode_responses=True
        )

        self.TASK_PREFIX = "car_report_task:"
        self.TASK_STATUS_PREFIX = "car_report_status:"
        self.TASK_RESULT_PREFIX = "car_report_result:"
        self.TASK_LIST_KEY = "car_report_tasks"

        self.STATUS_PENDING = "pending"
        self.STATUS_RUNNING = "running"
        self.STATUS_COMPLETED = "completed"
        self.STATUS_FAILED = "failed"

        self.TASK_EXPIRE_TIME = 24 * 60 * 60  # 24小时

        logger.info(f"Redis任务管理器初始化完成，连接到 {host}:{port}")

    def _get_task_key(self, task_id: str) -> str:
        return f"{self.TASK_PREFIX}{task_id}"

    def _get_status_key(self, task_id: str) -> str:
        return f"{self.TASK_STATUS_PREFIX}{task_id}"

    def _get_result_key(self, task_id: str) -> str:
        return f"{self.TASK_RESULT_PREFIX}{task_id}"

    def create_task(self, vin: str, new_date: str, qr_code_url: str = None) -> str:
        task_id = str(uuid.uuid4())

        task_data = {
            'task_id': task_id,
            'vin': vin,
            'new_date': new_date,
            'qr_code_url': qr_code_url or "https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg",
            'created_at': datetime.now().isoformat(),
            'status': self.STATUS_PENDING,
            'updated_at': datetime.now().isoformat()
        }

        self.redis_client.setex(
            self._get_task_key(task_id),
            self.TASK_EXPIRE_TIME,
            json.dumps(task_data, ensure_ascii=False)
        )

        self.redis_client.setex(
            self._get_status_key(task_id),
            self.TASK_EXPIRE_TIME,
            json.dumps({
                'status': self.STATUS_PENDING,
                'updated_at': datetime.now().isoformat()
            }, ensure_ascii=False)
        )

        self.redis_client.zadd(
            self.TASK_LIST_KEY,
            {task_id: datetime.now().timestamp()}
        )

        logger.info(f"创建任务: {task_id}, VIN: {vin}, 日期: {new_date}")
        return task_id

    def update_task_status(self, task_id: str, status: str, **kwargs) -> bool:
        try:
            status_data = {
                'status': status,
                'updated_at': datetime.now().isoformat(),
                **kwargs
            }

            self.redis_client.setex(
                self._get_status_key(task_id),
                self.TASK_EXPIRE_TIME,
                json.dumps(status_data, ensure_ascii=False)
            )

            task_key = self._get_task_key(task_id)
            task_data_str = self.redis_client.get(task_key)
            if task_data_str:
                task_data = json.loads(task_data_str)
                task_data['status'] = status
                task_data['updated_at'] = datetime.now().isoformat()
                self.redis_client.setex(
                    task_key,
                    self.TASK_EXPIRE_TIME,
                    json.dumps(task_data, ensure_ascii=False)
                )

            logger.info(f"更新任务状态: {task_id} -> {status}")
            return True

        except Exception as e:
            logger.error(f"更新任务状态失败: {task_id}, 错误: {e}")
            return False

    def save_task_result(self, task_id: str, success: bool, screenshot_path: str = None, error: str = None) -> bool:
        try:
            result_data = {
                'success': success,
                'screenshot_path': screenshot_path,
                'error': error,
                'completed_at': datetime.now().isoformat()
            }

            self.redis_client.setex(
                self._get_result_key(task_id),
                self.TASK_EXPIRE_TIME,
                json.dumps(result_data, ensure_ascii=False)
            )

            status = self.STATUS_COMPLETED if success else self.STATUS_FAILED
            self.update_task_status(task_id, status)

            logger.info(f"保存任务结果: {task_id}, 成功: {success}")
            return True

        except Exception as e:
            logger.error(f"保存任务结果失败: {task_id}, 错误: {e}")
            return False

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            task_info = {}

            task_data_str = self.redis_client.get(self._get_task_key(task_id))
            if task_data_str:
                task_info['task_data'] = json.loads(task_data_str)

            status_data_str = self.redis_client.get(
                self._get_status_key(task_id))
            if status_data_str:
                task_info['status_data'] = json.loads(status_data_str)

            result_data_str = self.redis_client.get(
                self._get_result_key(task_id))
            if result_data_str:
                task_info['result_data'] = json.loads(result_data_str)

            return task_info if task_info else None

        except Exception as e:
            logger.error(f"获取任务信息失败: {task_id}, 错误: {e}")
            return None

    def get_task_status(self, task_id: str) -> Optional[str]:
        try:
            status_data_str = self.redis_client.get(
                self._get_status_key(task_id))
            if status_data_str:
                status_data = json.loads(status_data_str)
                return status_data.get('status')
            return None
        except Exception as e:
            logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
            return None

    def get_all_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            # 使用 zrevrange 获取最新的任务（按时间戳降序），确保获取最新的任务
            task_ids = self.redis_client.zrevrange(
                self.TASK_LIST_KEY, 0, limit - 1)

            tasks = []
            for task_id in task_ids:
                task_info = self.get_task_info(task_id)
                if task_info:
                    combined_info = {
                        'task_id': task_id,
                        **task_info.get('task_data', {}),
                        **task_info.get('status_data', {}),
                        **task_info.get('result_data', {})
                    }
                    tasks.append(combined_info)

            # 再次按照创建时间排序，确保最新的在前面（双重保险）
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 确保返回的任务数量不超过限制
            return tasks[:limit]

        except Exception as e:
            logger.error(f"获取所有任务失败: {e}")
            return []

    def is_redis_connected(self) -> bool:
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其相关数据"""
        try:
            # 删除任务数据
            self.redis_client.delete(self._get_task_key(task_id))
            
            # 删除状态数据
            self.redis_client.delete(self._get_status_key(task_id))
            
            # 删除结果数据
            self.redis_client.delete(self._get_result_key(task_id))
            
            # 从任务列表中移除
            self.redis_client.zrem(self.TASK_LIST_KEY, task_id)
            
            logger.info(f"删除任务: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除任务失败: {task_id}, 错误: {e}")
            return False

    def clear_all_tasks(self) -> bool:
        """清空所有任务记录"""
        try:
            # 获取所有任务ID
            task_ids = self.redis_client.zrange(self.TASK_LIST_KEY, 0, -1)
            
            if not task_ids:
                logger.info("没有任务需要清空")
                return True
            
            # 批量删除所有任务相关数据
            pipeline = self.redis_client.pipeline()
            
            for task_id in task_ids:
                # 删除任务数据
                pipeline.delete(self._get_task_key(task_id))
                # 删除状态数据
                pipeline.delete(self._get_status_key(task_id))
                # 删除结果数据
                pipeline.delete(self._get_result_key(task_id))
            
            # 删除任务列表
            pipeline.delete(self.TASK_LIST_KEY)
            
            # 执行批量删除
            pipeline.execute()
            
            logger.info(f"成功清空 {len(task_ids)} 个任务记录")
            return True
            
        except Exception as e:
            logger.error(f"清空所有任务失败: {e}")
            return False


# 全局Redis任务管理器实例
redis_task_manager = None


def init_redis_task_manager(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD):
    global redis_task_manager
    redis_task_manager = RedisTaskManager(host, port, db, password)
    return redis_task_manager


def get_redis_task_manager() -> RedisTaskManager:
    global redis_task_manager
    if redis_task_manager is None:
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', 6379))
        db = int(os.getenv('REDIS_DB', 0))
        password = os.getenv('REDIS_PASSWORD')

        redis_task_manager = RedisTaskManager(host, port, db, password)

    return redis_task_manager
