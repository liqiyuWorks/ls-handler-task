#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze 知识库管理 Python 库

提供 Coze 知识库的完整管理功能，包括：
- 知识库列表查询
- 知识库文件列表查询
- 数据导出等功能

使用示例：
    from coze_scripts import CozeKnowledgeAPI
    
    # 初始化客户端
    api = CozeKnowledgeAPI(token="your_pat_token", space_id="your_space_id")
    
    # 获取知识库列表
    datasets = api.get_all_datasets(space_id="your_space_id")
    
    # 获取知识库文件列表
    files = api.get_all_knowledge_files(dataset_id="your_dataset_id", space_id="your_space_id")
"""

from .sync_rag import CozeKnowledgeAPI

__version__ = "1.0.0"
__all__ = ["CozeKnowledgeAPI"]
