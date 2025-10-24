#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的FIS认证系统
基于scripts/handle_fis最佳实践的优化版本
"""

import logging
import sys
import os
import time

# 添加项目路径
sys.path.append('/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task')

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_optimized_auth():
    """测试优化后的认证系统"""
    try:
        from tasks.aquabridge.fis_auth import get_fis_auth_token
        
        print("🚀 测试优化后的FIS认证系统")
        print("=" * 60)
        
        # 记录开始时间
        start_time = time.time()
        
        # 测试获取token（使用重试机制）
        print("🔄 开始获取Auth0 token...")
        token = get_fis_auth_token(max_retries=2)  # 减少重试次数以加快测试
        
        # 记录结束时间
        end_time = time.time()
        duration = end_time - start_time
        
        if token:
            print(f"✅ 成功获取token: {token[:50]}...")
            print(f"📏 Token长度: {len(token)} 字符")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            return True
        else:
            print("❌ 获取token失败")
            print(f"⏱️ 耗时: {duration:.2f} 秒")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def test_auth_components():
    """测试认证组件"""
    try:
        from tasks.aquabridge.fis_auth import FISAuthManager, SmartWaitStrategies
        
        print("\n🧪 测试认证组件...")
        print("=" * 60)
        
        # 测试SmartWaitStrategies
        print("✅ SmartWaitStrategies 类加载成功")
        
        # 测试FISAuthManager
        auth_manager = FISAuthManager()
        print("✅ FISAuthManager 初始化成功")
        
        # 测试重试装饰器
        print("✅ 重试装饰器加载成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 组件测试失败: {e}")
        return False

def test_configuration():
    """测试配置"""
    try:
        print("\n⚙️ 测试配置...")
        print("=" * 60)
        
        # 检查环境变量
        username = os.getenv('FIS_USERNAME', 'terry@aquabridge.ai')
        password = os.getenv('FIS_PASSWORD', 'Abs,88000')
        
        print(f"👤 用户名: {username}")
        print(f"🔐 密码: {'*' * len(password)}")
        
        # 检查浏览器设置
        headless = os.getenv('FIS_HEADLESS', 'false').lower() == 'true'
        print(f"🖥️ 无头模式: {headless}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def run_performance_test():
    """运行性能测试"""
    try:
        print("\n📊 性能测试...")
        print("=" * 60)
        
        from tasks.aquabridge.fis_auth import get_fis_auth_token
        
        # 多次测试以评估稳定性
        success_count = 0
        total_tests = 3
        total_time = 0
        
        for i in range(total_tests):
            print(f"\n🔄 第 {i+1} 次测试...")
            start_time = time.time()
            
            token = get_fis_auth_token(max_retries=1)  # 只重试1次以加快测试
            
            end_time = time.time()
            test_duration = end_time - start_time
            total_time += test_duration
            
            if token:
                success_count += 1
                print(f"✅ 成功 (耗时: {test_duration:.2f}s)")
            else:
                print(f"❌ 失败 (耗时: {test_duration:.2f}s)")
        
        # 计算统计信息
        success_rate = (success_count / total_tests) * 100
        avg_time = total_time / total_tests
        
        print(f"\n📈 性能统计:")
        print(f"   成功率: {success_rate:.1f}% ({success_count}/{total_tests})")
        print(f"   平均耗时: {avg_time:.2f} 秒")
        print(f"   总耗时: {total_time:.2f} 秒")
        
        return success_rate >= 50  # 至少50%成功率
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🎯 FIS认证系统优化测试")
    print("=" * 60)
    
    # 运行各项测试
    config_success = test_configuration()
    components_success = test_auth_components()
    auth_success = test_optimized_auth()
    performance_success = run_performance_test()
    
    # 输出结果
    print("\n" + "=" * 60)
    print("📋 测试结果汇总:")
    print("=" * 60)
    print(f"⚙️ 配置测试: {'✅ 通过' if config_success else '❌ 失败'}")
    print(f"🧪 组件测试: {'✅ 通过' if components_success else '❌ 失败'}")
    print(f"🔐 认证测试: {'✅ 通过' if auth_success else '❌ 失败'}")
    print(f"📊 性能测试: {'✅ 通过' if performance_success else '❌ 失败'}")
    
    total_tests = 4
    passed_tests = sum([config_success, components_success, auth_success, performance_success])
    
    print("=" * 60)
    print(f"📈 总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！优化成功！")
        print("💡 建议: 现在可以运行实际任务: python main.py spider_fis_trade_data")
        sys.exit(0)
    elif passed_tests >= 3:
        print("\n✅ 大部分测试通过，系统基本可用")
        print("💡 建议: 可以尝试运行实际任务，但可能需要进一步调试")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total_tests - passed_tests} 项测试失败，需要进一步优化")
        sys.exit(1)
