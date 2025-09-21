#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统 V3.0 简化版 - 快速开始
Quick Start for Ship Fuel Prediction System V3.0 Simplified

作者: 船舶油耗预测系统
日期: 2025-09-21
"""

import sys
import os

# 添加API模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

def main():
    """快速开始示例"""
    print("🚀 船舶油耗预测系统 V3.0 简化版")
    print("=" * 50)
    
    try:
        # 导入API
        from enhanced_fuel_api_v3 import EnhancedFuelAPIV3
        
        # 初始化API
        print("1. 初始化API...")
        api = EnhancedFuelAPIV3()
        
        # 基础预测
        print("\n2. 基础预测示例:")
        result = api.predict_enhanced(
            ship_type='Bulk Carrier',
            speed=12.0,
            dwt=75000
        )
        
        if 'predicted_consumption' in result:
            print(f"   散货船@12节: {result['predicted_consumption']}mt")
            print(f"   置信度: {result['confidence']}")
        
        # 增强预测
        print("\n3. 增强预测示例:")
        enhanced_result = api.predict_enhanced(
            ship_type='Container Ship',
            speed=18.0,
            dwt=120000,
            ship_age=5,
            load_condition='Laden',
            draft=14.0,
            length=350
        )
        
        if 'predicted_consumption' in enhanced_result:
            print(f"   集装箱船(5年船龄): {enhanced_result['predicted_consumption']}mt")
            print(f"   预测方法: {enhanced_result['method']}")
        
        print("\n✅ 快速开始完成!")
        print("\n💡 更多功能:")
        print("   • 启动API服务: cd api && python fastapi_server.py")
        print("   • 访问Swagger: http://localhost:8080/docs")
        print("   • 模型训练: cd api && python enhanced_fuel_predictor_v3.py")
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("请确保在正确的目录中运行此脚本")
    except Exception as e:
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    main()
