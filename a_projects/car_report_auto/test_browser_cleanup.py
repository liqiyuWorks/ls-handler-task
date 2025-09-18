#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试浏览器清理功能
"""

import asyncio
import time
from playwright_config import PlaywrightConfig

async def test_browser_cleanup():
    """测试浏览器清理功能"""
    print("🧪 开始测试浏览器清理功能...")
    
    # 测试前检查Chrome进程数量
    initial_count = PlaywrightConfig.get_system_chrome_process_count()
    print(f"📊 测试前Chrome进程数量: {initial_count}")
    
    # 启动浏览器
    print("🚀 启动浏览器...")
    async with PlaywrightConfig(headless=True) as config:
        # 导航到测试页面
        await config.navigate_to_page("https://www.baidu.com")
        await asyncio.sleep(2)
        
        # 检查启动后的进程数量
        after_start_count = PlaywrightConfig.get_system_chrome_process_count()
        print(f"📊 启动后Chrome进程数量: {after_start_count}")
        
        # 截图测试
        screenshot_path = await config.take_screenshot("test_cleanup")
        print(f"📸 截图保存到: {screenshot_path}")
    
    # 等待清理完成
    await asyncio.sleep(3)
    
    # 检查清理后的进程数量
    final_count = PlaywrightConfig.get_system_chrome_process_count()
    print(f"📊 清理后Chrome进程数量: {final_count}")
    
    # 验证清理效果
    if final_count <= initial_count:
        print("✅ 浏览器清理功能测试通过！")
    else:
        print(f"❌ 浏览器清理功能测试失败！进程数量从 {initial_count} 增加到 {final_count}")
    
    return final_count <= initial_count

async def test_force_cleanup():
    """测试强制清理功能"""
    print("\n🧪 开始测试强制清理功能...")
    
    # 启动多个浏览器实例
    print("🚀 启动多个浏览器实例...")
    browsers = []
    for i in range(3):
        config = PlaywrightConfig(headless=True)
        await config.start()
        browsers.append(config)
        await config.navigate_to_page("https://www.baidu.com")
        await asyncio.sleep(1)
    
    # 检查进程数量
    before_cleanup_count = PlaywrightConfig.get_system_chrome_process_count()
    print(f"📊 强制清理前Chrome进程数量: {before_cleanup_count}")
    
    # 执行强制清理
    print("🧹 执行强制清理...")
    await PlaywrightConfig.cleanup_all_chrome_processes()
    
    # 等待清理完成
    await asyncio.sleep(2)
    
    # 检查清理后进程数量
    after_cleanup_count = PlaywrightConfig.get_system_chrome_process_count()
    print(f"📊 强制清理后Chrome进程数量: {after_cleanup_count}")
    
    # 清理浏览器实例
    for config in browsers:
        await config.cleanup()
    
    # 验证清理效果
    if after_cleanup_count < before_cleanup_count:
        print("✅ 强制清理功能测试通过！")
        return True
    else:
        print(f"❌ 强制清理功能测试失败！进程数量从 {before_cleanup_count} 变为 {after_cleanup_count}")
        return False

async def main():
    """主测试函数"""
    print("🔬 开始浏览器清理功能综合测试...")
    
    # 测试1：基本清理功能
    test1_result = await test_browser_cleanup()
    
    # 测试2：强制清理功能
    test2_result = await test_force_cleanup()
    
    # 总结
    print("\n📋 测试结果总结:")
    print(f"   基本清理功能: {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"   强制清理功能: {'✅ 通过' if test2_result else '❌ 失败'}")
    
    if test1_result and test2_result:
        print("\n🎉 所有测试通过！浏览器清理功能工作正常。")
    else:
        print("\n⚠️ 部分测试失败，请检查清理功能实现。")

if __name__ == "__main__":
    asyncio.run(main())
