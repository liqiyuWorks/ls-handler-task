#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze 知识库文件列表获取脚本
根据 Coze Open API 文档获取知识库中的文件列表
"""

import os
import sys
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


def _print_401_hint(exc: Exception) -> None:
    """401 时打印鉴权排查提示"""
    res = getattr(exc, "response", None)
    if res is None or getattr(res, "status_code", None) != 401:
        return
    print("\n📌 鉴权排查建议：")
    print("  1. 确认使用 PAT（个人访问令牌），且已开通 listKnowledge 权限")
    print("  2. 在扣子控制台创建/更新令牌：https://www.coze.cn → 开发者设置 → API 令牌")
    print("  3. 若接口要求「指定空间」，设置 COZE_WORKSPACE_ID 后重试")
    print("     workspace_id 从空间 URL 获取，如 .../space/7439012204332711970/library → 7439012204332711970")


class CozeKnowledgeAPI:
    """Coze 知识库 API 客户端"""
    
    BASE_URL = "https://api.coze.cn"
    
    def __init__(self, token: str, space_id: Optional[str] = None):
        """
        初始化 API 客户端
        
        Args:
            token: Coze API Token (PAT token)
            space_id: 空间 ID（可选，某些 API 需要）
        """
        # 确保 token 不为空且去除首尾空格
        if not token or not token.strip():
            raise ValueError("Token 不能为空")
        
        self.token = token.strip()
        self.space_id = space_id.strip() if space_id else None
        
        # 按照 Coze API 文档要求：Authorization: Bearer {Access_Token}
        # 注意：Bearer 后面必须有一个空格
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # 如果提供了 space_id，添加到默认 headers 中
        if self.space_id:
            self.headers["X-Coze-Space-Id"] = self.space_id
    
    def _get_headers(self, space_id: Optional[str] = None) -> Dict[str, str]:
        """
        获取请求头，支持临时覆盖 space_id
        
        Args:
            space_id: 临时使用的空间 ID（可选）
            
        Returns:
            请求头字典
        """
        headers = self.headers.copy()
        if space_id:
            headers["X-Coze-Space-Id"] = space_id
        return headers
    
    def list_datasets(
        self,
        space_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        dataset_ids: Optional[List[str]] = None,
        name: Optional[str] = None,
        status: Optional[int] = None,
        order_by: Optional[str] = None,
        order: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取知识库（数据集）列表
        
        根据 Coze API 文档：https://www.coze.cn/open/docs/developer_guides/list_dataset
        接口地址：GET https://api.coze.cn/v1/datasets
        权限要求：dataset:query
        
        Args:
            space_id: 空间 ID（可选）。某些 API 版本可能需要此参数
            page: 页码，默认 1
            page_size: 每页数量，默认 20，最大 100
            dataset_ids: 知识库 ID 数组（可选）
            name: 知识库名称（可选），支持模糊搜索
            status: 知识库状态（可选）：1-正常，2-删除中，3-已删除，4-训练中，5-训练失败，6-上传失败
            order_by: 排序字段（可选）。可选值：created_at, updated_at, name
            order: 排序顺序（可选）。可选值：asc, desc
            
        Returns:
            包含知识库列表的响应数据
            
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        # 使用实际可用的端点 /v1/datasets
        url = f"{self.BASE_URL}/v1/datasets"
        
        # 根据实际 API，参数名是 page_num 而不是 page
        params = {
            "page_num": max(page, 1),
            "page_size": min(max(page_size, 1), 100)  # 限制在 1~100 范围内
        }
        
        # space_id 参数（某些 API 版本需要）
        if space_id:
            params["space_id"] = space_id.strip()
        
        # 可选参数（根据文档，但可能某些参数在当前 API 版本不支持）
        if name:
            params["name"] = name.strip()
        # 注意：dataset_ids, status, order_by, order 可能在某些 API 版本不支持
        # 暂时不添加，避免参数错误
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应内容: {e.response.text[:500]}")
                _print_401_hint(e)
            raise
    
    def get_all_datasets(
        self,
        space_id: Optional[str] = None,
        name: Optional[str] = None,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取所有知识库（数据集）列表（自动翻页）
        
        根据实际 API，响应格式：{"code": 0, "data": {"dataset_list": [...], "total": ...}}
        
        Args:
            space_id: 空间 ID（可选，但建议提供）
            name: 知识库名称（可选），支持模糊搜索
            page_size: 每页数量，默认 20，最大 100
            
        Returns:
            所有知识库的列表
        """
        all_datasets = []
        page = 1
        
        if space_id:
            print(f"📚 开始获取知识库列表（空间 ID: {space_id}）...")
        else:
            print(f"📚 开始获取知识库列表...")
        
        while True:
            try:
                result = self.list_datasets(
                    space_id=space_id,
                    page=page,
                    page_size=page_size,
                    name=name
                )
                
                # 根据实际 API，响应格式：{"code": 0, "data": {"dataset_list": [...], "total": ...}}
                if result.get("code") != 0:
                    print(f"❌ API 返回错误: {result.get('msg', '未知错误')}")
                    break
                
                data = result.get("data", {})
                # 实际 API 返回 dataset_list 字段
                datasets = data.get("dataset_list") or data.get("list", [])
                total = data.get("total", len(datasets))
                has_more = data.get("has_more")
                
                all_datasets.extend(datasets)
                
                print(f"✅ 已获取第 {page} 页，共 {len(datasets)} 个知识库（总计: {len(all_datasets)}/{total}）")
                
                # 判断是否还有下一页
                if has_more is False or len(datasets) == 0:
                    break
                elif has_more is None:
                    # 如果没有 has_more 字段，使用传统判断方式
                    if len(datasets) < page_size or (total > 0 and len(all_datasets) >= total):
                        break
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"❌ 获取第 {page} 页失败: {str(e)}")
                break
        
        print(f"✅ 完成！共获取 {len(all_datasets)} 个知识库")
        return all_datasets
    
    def list_knowledge_files(
        self, 
        dataset_id: str,
        space_id: Optional[str] = None,
        page: int = 1,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        获取知识库文件列表
        
        根据 Coze API 文档：https://www.coze.cn/open/docs/developer_guides/list_knowledge_files
        接口地址：POST https://api.coze.cn/open_api/knowledge/document/list
        权限要求：listDocument
        
        Args:
            dataset_id: 知识库 ID（必选），即 knowledge URL 中 knowledge 后的数字
            space_id: 空间 ID（可选），即 space URL 中 space 后的数字
            page: 分页页码，默认 1，从第一页开始
            size: 每页返回的数据量，默认 10
            
        Returns:
            包含文件列表的响应数据，格式：{"code": 0, "msg": "success", "document_infos": [...], "total": ...}
            
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = f"{self.BASE_URL}/open_api/knowledge/document/list"
        
        current_space_id = space_id or self.space_id
        if not current_space_id:
            raise ValueError("space_id 是必需的，请在初始化时提供或在此方法中指定")
        
        headers = self._get_headers(current_space_id)
        # 文档要求：Agw-Js-Conv 防止丢失数字类型参数的精度
        headers["Agw-Js-Conv"] = "1"
        
        # 请求体：dataset_id 必选，page/size 可选
        data = {
            "dataset_id": str(dataset_id).strip(),
            "page": max(1, int(page)),
            "size": max(1, min(int(size), 100))
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                body = response.text
                if body.strip():
                    try:
                        err = response.json()
                        body = json.dumps(err, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                print(f"❌ 请求失败: HTTP {response.status_code}")
                print(f"响应: {body[:800]}")
                response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                _print_401_hint(e)
            raise
    
    def get_all_knowledge_files(
        self, 
        dataset_id: str,
        space_id: Optional[str] = None,
        page_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取知识库中的所有文件（自动翻页）
        
        根据 API 文档，响应格式：{"code": 0, "msg": "success", "document_infos": [...], "total": ...}
        
        Args:
            dataset_id: 知识库 ID
            space_id: 空间 ID（可选，如果初始化时未提供，可在此处指定）
            page_size: 每页数量，默认 10
            
        Returns:
            所有文件的列表
        """
        all_files = []
        page = 1  # 文档默认从第一页开始
        
        print(f"📚 开始获取知识库 {dataset_id} 的文件列表...")
        
        while True:
            try:
                result = self.list_knowledge_files(
                    dataset_id=dataset_id,
                    space_id=space_id,
                    page=page,
                    size=page_size
                )
                
                if result.get("code") != 0:
                    print(f"❌ API 返回错误: {result.get('msg', '未知错误')}")
                    break
                
                document_infos = result.get("document_infos", [])
                total = result.get("total", len(document_infos))
                
                all_files.extend(document_infos)
                
                print(f"✅ 已获取第 {page} 页，共 {len(document_infos)} 个文件（总计: {len(all_files)}/{total}）")
                
                if len(document_infos) < page_size or (total > 0 and len(all_files) >= total):
                    break
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"❌ 获取第 {page} 页失败: {str(e)}")
                break
        
        print(f"✅ 完成！共获取 {len(all_files)} 个文件")
        return all_files
    
    def get_file_detail(self, file_id: str, knowledge_id: str) -> Dict[str, Any]:
        """
        获取文件详情
        
        Args:
            file_id: 文件 ID
            knowledge_id: 知识库 ID
            
        Returns:
            文件详情数据
        """
        url = f"{self.BASE_URL}/open_api/v2/knowledge/files/{file_id}"
        
        params = {
            "knowledge_id": knowledge_id
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取文件详情失败: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"响应内容: {e.response.text}")
            raise


def format_timestamp(timestamp: Any) -> str:
    """格式化时间戳为可读格式"""
    if timestamp is None:
        return "N/A"
    try:
        if isinstance(timestamp, (int, float)):
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(timestamp, str):
            # 处理 ISO 格式字符串
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                return timestamp
        return str(timestamp)
    except (ValueError, OSError, OverflowError):
        return str(timestamp)


def print_datasets_summary(datasets: List[Dict[str, Any]]):
    """
    打印知识库列表摘要
    
    Args:
        datasets: 知识库列表
    """
    if not datasets:
        print("📝 没有找到知识库")
        return
    
    print(f"\n{'='*80}")
    print(f"📚 知识库列表摘要（共 {len(datasets)} 个知识库）")
    print(f"{'='*80}\n")
    
    for idx, dataset_info in enumerate(datasets, 1):
        # 根据实际 API 返回，字段名是 dataset_id
        dataset_id = dataset_info.get("dataset_id") or dataset_info.get("id") or "N/A"
        dataset_name = dataset_info.get("name") or "N/A"
        description = dataset_info.get("description") or ""
        
        # 状态信息（1-正常，2-删除中，3-已删除，4-训练中，5-训练失败，6-上传失败）
        status = dataset_info.get("status", "N/A")
        status_map = {1: "正常", 2: "删除中", 3: "已删除", 4: "训练中", 5: "训练失败", 6: "上传失败"}
        status_str = status_map.get(status, f"未知({status})") if isinstance(status, int) else str(status)
        
        # 文件信息
        file_list = dataset_info.get("file_list", [])
        file_count = len(file_list) if isinstance(file_list, list) else 0
        
        # 大小信息（实际 API 返回 all_file_size 字符串）
        all_file_size = dataset_info.get("all_file_size")
        if all_file_size:
            try:
                size_bytes = int(all_file_size)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.2f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
            except (ValueError, TypeError):
                size_str = str(all_file_size)
        else:
            size_str = "N/A"
        
        # 统计信息
        slice_count = dataset_info.get("slice_count", 0)
        hit_count = dataset_info.get("hit_count", 0)
        doc_count = dataset_info.get("doc_count", 0)
        format_type = dataset_info.get("format_type", "N/A")
        creator_name = dataset_info.get("creator_name", "")
        
        # 时间信息（实际 API 返回 Unix 时间戳）
        created_at = format_timestamp(dataset_info.get("create_time") or dataset_info.get("created_at"))
        updated_at = format_timestamp(dataset_info.get("update_time") or dataset_info.get("updated_at"))
        
        print(f"{idx}. {dataset_name}")
        print(f"   ID: {dataset_id}")
        print(f"   状态: {status_str}")
        print(f"   类型: {format_type}")
        print(f"   文件数: {file_count}")
        if file_list and len(file_list) > 0:
            print(f"   文件列表: {', '.join(file_list[:5])}{' ...' if len(file_list) > 5 else ''}")
        print(f"   总大小: {size_str}")
        print(f"   分段数: {slice_count}")
        print(f"   文档数: {doc_count}")
        print(f"   命中数: {hit_count}")
        if creator_name:
            print(f"   创建者: {creator_name}")
        if description:
            print(f"   描述: {description[:100]}{'...' if len(description) > 100 else ''}")
        print(f"   创建时间: {created_at}")
        print(f"   更新时间: {updated_at}")
        print()


def print_files_summary(files: List[Dict[str, Any]]):
    """
    打印文件列表摘要
    
    根据 API 文档，DocumentInfo 对象包含：document_id, name, type, size, status, format_type 等字段
    
    Args:
        files: 文件列表（DocumentInfo 对象数组）
    """
    if not files:
        print("📝 知识库中没有文件")
        return
    
    print(f"\n{'='*80}")
    print(f"📋 文件列表摘要（共 {len(files)} 个文件）")
    print(f"{'='*80}\n")
    
    for idx, file_info in enumerate(files, 1):
        # 根据 API 文档，字段名是 document_id
        document_id = file_info.get("document_id") or file_info.get("id") or "N/A"
        file_name = file_info.get("name") or "N/A"
        file_type = file_info.get("type") or "N/A"
        
        # 文件大小（字节）
        size = file_info.get("size", 0)
        if size:
            try:
                size_bytes = int(size)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.2f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
            except (ValueError, TypeError):
                size_str = str(size)
        else:
            size_str = "N/A"
        
        # 状态信息（0: 待处理, 1: 处理完毕, 2: 处理失败）
        status = file_info.get("status", "N/A")
        status_map = {0: "待处理", 1: "处理完毕", 2: "处理失败"}
        status_str = status_map.get(status, f"未知({status})") if isinstance(status, int) else str(status)
        
        # 格式类型（0: 表格, 1: 网页, 2: 图片, 3: txt/pdf/docx）
        format_type = file_info.get("format_type", "N/A")
        format_map = {0: "表格", 1: "网页", 2: "图片", 3: "文档"}
        format_str = format_map.get(format_type, f"未知({format_type})") if isinstance(format_type, int) else str(format_type)
        
        # 上传方式（0: 上传文件, 1: 上传在线链接）
        source_type = file_info.get("source_type", "N/A")
        source_map = {0: "上传文件", 1: "上传在线链接"}
        source_str = source_map.get(source_type, f"未知({source_type})") if isinstance(source_type, int) else str(source_type)
        
        # 统计信息
        slice_count = file_info.get("slice_count", 0)
        hit_count = file_info.get("hit_count", 0)
        chat_count = file_info.get("chat_count", 0)
        
        # 时间信息（Unix 时间戳）
        created_at = format_timestamp(file_info.get("create_time") or file_info.get("created_at"))
        updated_at = format_timestamp(file_info.get("update_time") or file_info.get("updated_at"))
        
        print(f"{idx}. {file_name}")
        print(f"   ID: {document_id}")
        print(f"   类型: {file_type} ({format_str})")
        print(f"   大小: {size_str}")
        print(f"   状态: {status_str}")
        print(f"   上传方式: {source_str}")
        print(f"   分段数: {slice_count}")
        print(f"   命中数: {hit_count}")
        if chat_count:
            print(f"   字数: {chat_count}")
        print(f"   创建时间: {created_at}")
        print(f"   更新时间: {updated_at}")
        print()


def save_datasets_to_json(datasets: List[Dict[str, Any]], output_path: str = "knowledge_datasets.json"):
    """
    将知识库列表保存到 JSON 文件
    
    Args:
        datasets: 知识库列表
        output_path: 输出文件路径
    """
    output_data = {
        "export_time": datetime.now().isoformat(),
        "total": len(datasets),
        "datasets": datasets
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 知识库列表已保存到: {output_path}")


def save_files_to_json(files: List[Dict[str, Any]], output_path: str = "knowledge_files.json"):
    """
    将文件列表保存到 JSON 文件
    
    Args:
        files: 文件列表
        output_path: 输出文件路径
    """
    output_data = {
        "export_time": datetime.now().isoformat(),
        "total": len(files),
        "files": files
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 文件列表已保存到: {output_path}")


def main():
    """主函数"""
    # 从环境变量或默认值获取配置，并去除首尾空格和换行符
    token_raw = os.getenv("COZE_TOKEN") or os.getenv("COZE_API_TOKEN") or "pat_ESpGyZR84pzIr8AMLhdpMbeFYxpZndnLNdOOaDpEvuVnD6ctWEh1yg6d71JnzOLl"
    token = token_raw.strip().replace('\n', '').replace('\r', '') if token_raw else None
    
    knowledge_id = (os.getenv("COZE_KNOWLEDGE_ID") or "7598823790127366163").strip()
    
    # 解析命令行参数
    # 支持的模式：
    # 1. python sync_rag.py list - 列出所有知识库
    # 2. python sync_rag.py files [knowledge_id] - 列出指定知识库的文件
    # 3. python sync_rag.py <token> [knowledge_id] - 兼容旧版本用法
    
    mode = "files"  # 默认模式：查看文件列表
    if len(sys.argv) > 1:
        first_arg = sys.argv[1].lower()
        if first_arg in ["list", "datasets", "knowledge"]:
            mode = "list"
        elif first_arg in ["files", "file"]:
            mode = "files"
            if len(sys.argv) > 2:
                knowledge_id = sys.argv[2].strip()
        elif first_arg.startswith("sk-") or first_arg.startswith("pat_"):
            # 兼容旧版本：第一个参数是 token
            token = sys.argv[1].strip()
            if len(sys.argv) > 2:
                knowledge_id = sys.argv[2].strip()
        else:
            # 如果第一个参数不是模式，可能是 knowledge_id
            knowledge_id = sys.argv[1].strip()
    
    # 检查必要的参数
    if not token:
        print("❌ 错误: 未提供 Coze API Token")
        print("\n使用方法:")
        print("  查看知识库列表:")
        print("    python sync_rag.py list")
        print("  查看知识库文件:")
        print("    python sync_rag.py files [knowledge_id]")
        print("  或使用环境变量:")
        print("    export COZE_TOKEN='your_token'")
        print("    export COZE_KNOWLEDGE_ID='your_knowledge_id'")
        sys.exit(1)
    
    # 获取 space_id（某些 API 需要）
    space_id = (os.getenv("COZE_WORKSPACE_ID") or "7487472502496231460").strip() or None
    
    # 创建 API 客户端
    api = CozeKnowledgeAPI(token=token, space_id=space_id)
    
    try:
        if mode == "list":
            # 列出所有知识库
            print("=" * 80)
            print("📚 获取知识库列表")
            print("=" * 80)
            
            # 根据实际 API，可能需要 space_id 参数（从环境变量获取）
            space_id = (os.getenv("COZE_WORKSPACE_ID") or "7487472502496231460").strip() or None
            if space_id:
                print(f"   使用空间 ID: {space_id}")
            
            datasets = api.get_all_datasets(space_id=space_id)
            
            # 打印摘要
            print_datasets_summary(datasets)
            
            # 保存到 JSON 文件
            output_file = f"knowledge_datasets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_datasets_to_json(datasets, output_file)
            
            return datasets
            
        else:
            # 查看指定知识库的文件列表
            if not knowledge_id:
                print("❌ 错误: 未提供知识库 ID")
                print("\n使用方法:")
                print("  python sync_rag.py files <knowledge_id>")
                print("  或设置环境变量: export COZE_KNOWLEDGE_ID='your_knowledge_id'")
                sys.exit(1)
            
            print("=" * 80)
            print(f"📋 获取知识库 {knowledge_id} 的文件列表")
            print("=" * 80)
            
            # 获取 space_id（文件列表 API 需要）
            space_id = (os.getenv("COZE_WORKSPACE_ID") or "7487472502496231460").strip() or None
            if space_id:
                print(f"   使用空间 ID: {space_id}")
            
            files = api.get_all_knowledge_files(dataset_id=knowledge_id, space_id=space_id)
            
            # 打印摘要
            print_files_summary(files)
            
            # 保存到 JSON 文件
            output_file = f"knowledge_files_{knowledge_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_files_to_json(files, output_file)
            
            return files
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
