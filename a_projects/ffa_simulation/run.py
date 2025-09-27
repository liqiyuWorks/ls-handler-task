#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统启动脚本
"""

import uvicorn
import os
import sys
from database import create_tables

def main():
    """主函数"""
    print("=" * 60)
    print("FFA模拟交易系统")
    print("=" * 60)
    
    # 创建必要的目录
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    # 创建数据库表
    print("正在初始化数据库...")
    create_tables()
    print("数据库初始化完成")
    
    # 启动服务器
    print("\n正在启动服务器...")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("按 Ctrl+C 停止服务器")
    print("-" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
