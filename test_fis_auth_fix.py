#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试FIS认证修复
验证修复后的认证流程是否正常工作
"""

import logging
import sys
import os

# 添加项目路径
sys.path.append('/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task')

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_fis_auth():
    """测试FIS认证功能"""
    try:
        from tasks.aquabridge.fis_auth import get_fis_auth_token
        
        print("开始测试FIS认证...")
        print("=" * 50)
        
        # 测试获取token（使用重试机制）
        token = get_fis_auth_token(max_retries=2)  # 减少重试次数以加快测试
        
        if token:
            print(f"✅ 成功获取token: {token[:50]}...")
            return True
        else:
            print("❌ 获取token失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def test_fis_unified_spider():
    """测试FIS统一爬虫"""
    try:
        from tasks.aquabridge.fis_unified_spider import FISUnifiedSpider
        
        print("\n开始测试FIS统一爬虫...")
        print("=" * 50)
        
        # 创建爬虫实例
        spider = FISUnifiedSpider()
        
        if spider.auth_token:
            print(f"✅ 爬虫初始化成功，token: {spider.auth_token[:50]}...")
            return True
        else:
            print("❌ 爬虫初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ 爬虫测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    print("FIS认证修复测试")
    print("=" * 50)
    
    # 测试认证功能
    auth_success = test_fis_auth()
    
    # 测试统一爬虫
    spider_success = test_fis_unified_spider()
    
    # 输出结果
    print("\n" + "=" * 50)
    print("测试结果:")
    print(f"认证功能: {'✅ 通过' if auth_success else '❌ 失败'}")
    print(f"统一爬虫: {'✅ 通过' if spider_success else '❌ 失败'}")
    
    if auth_success and spider_success:
        print("\n🎉 所有测试通过！修复成功！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查日志")
        sys.exit(1)
