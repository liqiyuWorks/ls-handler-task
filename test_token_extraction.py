#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进的token提取功能
专门用于调试和验证token获取过程
"""

import logging
import sys
import os
import time

# 添加项目路径
sys.path.append('/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task')

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_enhanced_token_extraction():
    """测试增强的token提取功能"""
    try:
        from tasks.aquabridge.fis_auth import get_fis_auth_token
        
        print("🔍 测试增强的token提取功能")
        print("=" * 60)
        print("📝 这个测试会显示详细的调试信息，帮助我们了解token提取过程")
        print("⏱️ 请耐心等待，整个过程可能需要1-2分钟")
        print("=" * 60)
        
        # 记录开始时间
        start_time = time.time()
        
        # 测试获取token（使用重试机制）
        print("🔄 开始获取Auth0 token...")
        token = get_fis_auth_token(max_retries=2)  # 减少重试次数以加快测试
        
        # 记录结束时间
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("📊 测试结果:")
        print("=" * 60)
        
        if token:
            print(f"✅ 成功获取token!")
            print(f"🔑 Token: {token[:50]}...{token[-20:]}")
            print(f"📏 Token长度: {len(token)} 字符")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            
            # 验证token格式
            if token.startswith('Bearer '):
                print("✅ Token格式正确 (Bearer格式)")
            elif len(token) > 100:
                print("✅ Token长度合理")
            else:
                print("⚠️ Token长度较短，可能不是完整的token")
            
            return True
        else:
            print("❌ 获取token失败")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            print("\n💡 建议:")
            print("1. 检查网络连接")
            print("2. 确认用户名和密码正确")
            print("3. 查看上面的详细日志了解失败原因")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_debug_mode():
    """测试调试模式"""
    try:
        print("\n🐛 测试调试模式...")
        print("=" * 60)
        
        # 设置环境变量启用调试
        os.environ['FIS_HEADLESS'] = 'false'  # 显示浏览器窗口
        os.environ['FIS_LOG_LEVEL'] = 'DEBUG'  # 详细日志
        
        print("🔧 调试设置:")
        print(f"   无头模式: {os.getenv('FIS_HEADLESS', 'true')}")
        print(f"   日志级别: {os.getenv('FIS_LOG_LEVEL', 'INFO')}")
        print(f"   用户名: {os.getenv('FIS_USERNAME', 'terry@aquabridge.ai')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试模式设置失败: {e}")
        return False

if __name__ == "__main__":
    print("🎯 FIS Token提取功能测试")
    print("=" * 60)
    print("📋 这个测试专门用于调试token提取问题")
    print("🔍 会显示详细的调试信息帮助定位问题")
    print("=" * 60)
    
    # 运行测试
    debug_success = test_debug_mode()
    extraction_success = test_enhanced_token_extraction()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📋 测试结果汇总:")
    print("=" * 60)
    print(f"🐛 调试模式: {'✅ 通过' if debug_success else '❌ 失败'}")
    print(f"🔍 Token提取: {'✅ 通过' if extraction_success else '❌ 失败'}")
    
    if extraction_success:
        print("\n🎉 Token提取测试成功！")
        print("💡 现在可以运行实际任务: python main.py spider_fis_trade_data")
        sys.exit(0)
    else:
        print("\n⚠️ Token提取测试失败")
        print("💡 请查看上面的详细日志，根据错误信息进行调试")
        print("🔧 建议:")
        print("   1. 检查网络连接")
        print("   2. 确认FIS网站可以正常访问")
        print("   3. 验证用户名和密码")
        print("   4. 查看浏览器窗口（如果headless=false）")
        sys.exit(1)
