# -*- coding: utf-8 -*-
"""
Coze 知识库服务
封装与 Coze Open API 的交互逻辑
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any

class CozeService:
    """Coze 知识库 API 客户端服务"""
    
    BASE_URL = "https://api.coze.cn"
    
    def __init__(self, token: str, space_id: Optional[str] = None):
        """
        初始化 API 客户端
        
        Args:
            token: Coze API Token (PAT token)
            space_id: 空间 ID（可选，某些 API 需要）
        """
        if not token or not token.strip():
            raise ValueError("Token 不能为空")
        
        self.token = token.strip()
        self.space_id = space_id.strip() if space_id else None
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        if self.space_id:
            self.headers["X-Coze-Space-Id"] = self.space_id
    
    def _get_headers(self, space_id: Optional[str] = None) -> Dict[str, str]:
        """获取请求头，支持临时覆盖 space_id"""
        headers = self.headers.copy()
        if space_id:
            headers["X-Coze-Space-Id"] = space_id
        return headers
    
    def list_datasets(
        self,
        space_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取知识库列表"""
        url = f"{self.BASE_URL}/v1/datasets"
        
        params = {
            "page_num": max(page, 1),
            "page_size": min(max(page_size, 1), 100)
        }
        
        if space_id:
            params["space_id"] = space_id.strip()
        elif self.space_id:
            params["space_id"] = self.space_id
            
        if name:
            params["name"] = name.strip()
            
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def list_files(
        self,
        dataset_id: str,
        space_id: Optional[str] = None,
        page: int = 1,
        size: int = 10
    ) -> Dict[str, Any]:
        """获取知识库文件列表"""
        url = f"{self.BASE_URL}/open_api/knowledge/document/list"
        
        current_space_id = space_id or self.space_id
        if not current_space_id:
            raise ValueError("space_id 是必需的")
        
        headers = self._get_headers(current_space_id)
        headers["Agw-Js-Conv"] = "1"
        
        data = {
            "dataset_id": str(dataset_id).strip(),
            "page": max(1, int(page)),
            "size": max(1, min(int(size), 100))
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()

    def upload_file(
        self,
        dataset_id: str,
        file_content: bytes,
        file_name: str,
        space_id: Optional[str] = None,
        process_mode: str = "increment"
    ) -> Dict[str, Any]:
        """
        上传文件到知识库
        """
        sid = space_id or self.space_id
        if not sid:
            raise ValueError("space_id 必需")
        
        url = f"{self.BASE_URL}/open_api/knowledge/document/create"
        headers = {k: v for k, v in self.headers.items() if k.lower() != "content-type"}
        headers["Agw-Js-Conv"] = "1"
        if sid and "X-Coze-Space-Id" not in headers:
            headers["X-Coze-Space-Id"] = str(sid)
        
        data = {
            "space_id": str(sid),
            "dataset_id": str(dataset_id).strip(),
            "name": file_name.strip(),
            "document_type": "file",
            "process_mode": process_mode.strip() or "increment",
        }
        
        files = [("file", (file_name, file_content, "application/octet-stream"))]
        
        response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        
        if response.status_code != 200:
            # Try to return the error message from Coze
             try:
                error_detail = response.json()
                raise Exception(f"Coze API Error: {error_detail.get('msg', response.text)}")
             except ValueError:
                response.raise_for_status()

        return response.json()

    def add_url(
        self,
        dataset_id: str,
        url: str,
        name: str,
        space_id: Optional[str] = None,
        update_interval: int = 24
    ) -> Dict[str, Any]:
        """添加 URL 到知识库"""
        sid = space_id or self.space_id
        if not sid:
            raise ValueError("space_id 必需")
            
        url_endpoint = f"{self.BASE_URL}/open_api/knowledge/document/create"
        
        document_bases = [{
            "name": name,
            "source_info": {
                "web_url": url,
                "document_source": 1
            },
            "update_rule": {
                "update_type": 1,
                "update_interval": int(update_interval)
            }
        }]
        
        payload = {
            "dataset_id": str(dataset_id),
            "document_bases": document_bases,
            "chunk_strategy": {
                "separator": "\n\n",
                "max_tokens": 800,
                "remove_extra_spaces": False,
                "remove_urls_emails": False,
                "chunk_type": 1
            }
        }
        
        headers = self._get_headers(sid)
        headers["Agw-Js-Conv"] = "1"
        
        response = requests.post(url_endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    def add_urls_batch(
        self,
        dataset_id: str,
        urls: List[Dict[str, str]],
        space_id: Optional[str] = None,
        update_interval: int = 24
    ) -> Dict[str, Any]:
        """批量添加 URL 到知识库"""
        sid = space_id or self.space_id
        if not sid:
            raise ValueError("space_id 必需")
            
        url_endpoint = f"{self.BASE_URL}/open_api/knowledge/document/create"
        
        document_bases = []
        for item in urls:
            document_bases.append({
                "name": item['name'],
                "source_info": {
                    "web_url": item['url'],
                    "document_source": 1
                },
                "update_rule": {
                    "update_type": 1,
                    "update_interval": int(update_interval)
                }
            })
        
        payload = {
            "dataset_id": str(dataset_id),
            "document_bases": document_bases,
            "chunk_strategy": {
                "separator": "\n\n",
                "max_tokens": 800,
                "remove_extra_spaces": False,
                "remove_urls_emails": False,
                "chunk_type": 1
            }
        }
        
        headers = self._get_headers(sid)
        headers["Agw-Js-Conv"] = "1"
        
        response = requests.post(url_endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
