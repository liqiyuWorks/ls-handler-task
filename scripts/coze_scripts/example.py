#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze 知识库管理库使用示例

演示如何使用 CozeKnowledgeAPI 进行知识库管理
"""

import os
from sync_rag import CozeKnowledgeAPI

def main():
    # 从环境变量获取配置
    token = os.getenv("COZE_TOKEN", "your_pat_token")
    space_id = os.getenv("COZE_WORKSPACE_ID", "your_space_id")
    
    # 初始化 API 客户端
    api = CozeKnowledgeAPI(token=token, space_id=space_id)
    
    print("=" * 80)
    print("📚 Coze 知识库管理示例")
    print("=" * 80)
    
    # 示例 1: 获取所有知识库列表
    print("\n1. 获取所有知识库列表...")
    try:
        datasets = api.get_all_datasets(space_id=space_id)
        print(f"✅ 成功获取 {len(datasets)} 个知识库")
        
        # 显示前 3 个知识库
        for idx, dataset in enumerate(datasets[:3], 1):
            print(f"   {idx}. {dataset.get('name')} (ID: {dataset.get('dataset_id')})")
    except Exception as e:
        print(f"❌ 获取知识库列表失败: {str(e)}")
    
    # 示例 2: 获取指定知识库的文件列表
    print("\n2. 获取知识库文件列表...")
    dataset_id = os.getenv("COZE_KNOWLEDGE_ID", "7598823790127366163")
    try:
        files = api.get_all_knowledge_files(
            dataset_id=dataset_id,
            space_id=space_id
        )
        print(f"✅ 成功获取 {len(files)} 个文件")
        
        # 显示文件信息
        for idx, file_info in enumerate(files[:5], 1):
            file_name = file_info.get('name', 'N/A')
            file_size = file_info.get('size', 0)
            status = file_info.get('status', 'N/A')
            print(f"   {idx}. {file_name} ({file_size} 字节, 状态: {status})")
    except Exception as e:
        print(f"❌ 获取文件列表失败: {str(e)}")
        print("   提示: 请确保:")
        print("   1. Token 具有 listDocument 权限")
        print("   2. space_id 正确")
        print("   3. dataset_id 属于指定的 space_id")
    
    # 示例 3: 获取单页知识库列表
    print("\n3. 获取单页知识库列表...")
    try:
        result = api.list_datasets(
            space_id=space_id,
            page=1,
            page_size=10
        )
        if result.get("code") == 0:
            data = result.get("data", {})
            datasets = data.get("dataset_list", [])
            total = data.get("total", 0)
            print(f"✅ 第 1 页: {len(datasets)}/{total} 个知识库")
        else:
            print(f"❌ API 返回错误: {result.get('msg')}")
    except Exception as e:
        print(f"❌ 获取单页知识库列表失败: {str(e)}")
    
    # 示例 4: 获取单页文件列表
    print("\n4. 获取单页文件列表...")
    try:
        result = api.list_knowledge_files(
            dataset_id=dataset_id,
            space_id=space_id,
            page=1,
            size=10
        )
        if result.get("code") == 0:
            document_infos = result.get("document_infos", [])
            total = result.get("total", 0)
            print(f"✅ 第 1 页: {len(document_infos)}/{total} 个文件")
        else:
            print(f"❌ API 返回错误: {result.get('msg')}")
    except Exception as e:
        print(f"❌ 获取单页文件列表失败: {str(e)}")
        print("   提示: 请确保 Token 具有 listDocument 权限")

    # 示例 5: 上传本地文件（需有可用的 .txt/.pdf 等）
    print("\n5. 创建知识库文件（上传本地文件 / 添加在线网页）...")
    try:
        test_txt = os.path.join(os.path.dirname(__file__) or ".", "_test_upload.txt")
        if os.path.isfile(test_txt):
            res = api.create_document_from_file(
                dataset_id=dataset_id,
                file_path=test_txt,
                space_id=space_id,
            )
            print(f"✅ 上传成功: {res.get('data', res).get('document_id', 'N/A')}")
        else:
            res = api.create_document_from_url(
                dataset_id=dataset_id,
                url="https://www.coze.cn/",
                name="扣子官网",
                space_id=space_id,
            )
            print(f"✅ 添加网页成功: {res.get('data', res).get('document_id', 'N/A')}")
    except Exception as e:
        print(f"❌ 创建失败: {str(e)}")
        print("   提示: 需 create 相关权限；确认 space_id、dataset_id 正确")


if __name__ == "__main__":
    main()
