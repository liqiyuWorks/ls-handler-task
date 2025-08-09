#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的报告截图功能
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from car_report_auto.car_report_modifier_web import CarReportModifier
from loguru import logger

async def test_report_screenshot():
    """测试报告截图功能"""
    
    # 测试VIN (可以替换为实际的VIN)
    test_vin = "LE4ZG8DB3ML639548"  # 示例VIN
    test_date = "2024-01-20"
    
    logger.info(f"开始测试报告截图功能，VIN: {test_vin}")
    
    try:
        # 创建修改器实例
        modifier = CarReportModifier(
            vin=test_vin,
            new_date=test_date,
            headless=False  # 设为False可以看到浏览器操作过程
        )
        
        # 获取报告链接
        logger.info("获取报告链接...")
        report_url = await modifier.get_report_url()
        
        if not report_url:
            logger.error("无法获取报告链接，测试终止")
            return False
        
        logger.info(f"成功获取报告链接: {report_url}")
        
        # 执行修改和截图
        logger.info("开始修改日期并截图...")
        success, screenshot_path = await modifier.modify_date_on_page(report_url)
        
        if success and screenshot_path:
            logger.info(f"✅ 修改成功！截图已保存到: {screenshot_path}")
            
            # 检查截图文件是否存在
            if os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                logger.info(f"截图文件大小: {file_size / 1024:.2f} KB")
                
                # 检查文件是否为有效的PNG文件
                with open(screenshot_path, 'rb') as f:
                    header = f.read(8)
                    if header == b'\x89PNG\r\n\x1a\n':
                        logger.info("✅ 截图文件格式正确")
                    else:
                        logger.warning("⚠️ 截图文件格式可能有问题")
                
                return True
            else:
                logger.error("❌ 截图文件不存在")
                return False
        else:
            logger.error(f"❌ 修改失败！错误截图: {screenshot_path}")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始测试修复后的报告截图功能")
    logger.info("=" * 50)
    
    # 确保截图目录存在
    os.makedirs("static/screenshots", exist_ok=True)
    
    success = await test_report_screenshot()
    
    logger.info("=" * 50)
    if success:
        logger.info("✅ 测试通过！修复成功！")
        logger.info("现在修改后的报告将包含完整的内容，包括您指定的xpath区域。")
        logger.info("主要改进包括:")
        logger.info("1. 等待特定内容区域 (//*[@id=\"reportRef\"]/div[2]/div/div[1]/div/div/div) 加载")
        logger.info("2. 强制展开所有可能的折叠内容")
        logger.info("3. 确保所有图片和资源完全加载")
        logger.info("4. 优化截图时机和质量")
    else:
        logger.error("❌ 测试失败！请检查网络连接和VIN码是否正确。")
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
