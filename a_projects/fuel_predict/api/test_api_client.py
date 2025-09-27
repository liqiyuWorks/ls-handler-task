#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI客户端测试脚本
FastAPI Client Test Script

测试船舶油耗预测FastAPI服务的各项功能

作者: 船舶油耗预测系统
日期: 2025-09-21
"""

import requests
import json
from datetime import datetime

# API服务器地址
API_BASE_URL = "http://localhost:8080"

class FuelPredictionClient:
    """油耗预测API客户端"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health(self):
        """测试健康检查"""
        print("🔍 测试健康检查...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 服务状态: {data['status']}")
                print(f"   📅 版本: {data['version']}")
                return True
            else:
                print(f"   ❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ 连接失败: {e}")
            return False
    
    def test_basic_prediction_get(self):
        """测试基础预测 (GET方式)"""
        print("\n📊 测试基础预测 (GET方式)...")
        
        params = {
            "ship_type": "Bulk Carrier",
            "speed": 12.0,
            "dwt": 75000,
            "ship_age": 8,
            "load_condition": "Laden"
        }
        
        try:
            response = self.session.get(f"{self.base_url}/predict", params=params)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 预测成功")
                print(f"   🚢 船舶: {data['ship_type']} @ {data['speed']}节")
                print(f"   ⛽ 预测油耗: {data['predicted_consumption']}mt")
                print(f"   📈 置信度: {data['confidence']}")
                print(f"   🔧 方法: {data['method']}")
                return data
            else:
                print(f"   ❌ 预测失败: {response.status_code}")
                print(f"   错误: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def test_enhanced_prediction_post(self):
        """测试增强预测 (POST方式)"""
        print("\n🚀 测试增强预测 (POST方式)...")
        
        payload = {
            "ship_type": "Container Ship",
            "speed": 18.0,
            "dwt": 120000,
            "ship_age": 5,
            "load_condition": "Laden",
            "draft": 14.0,
            "length": 350,
            "latitude": 35.0,
            "longitude": 139.0,
            "heavy_fuel_cp": 650,
            "light_fuel_cp": 850
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/predict", 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 增强预测成功")
                print(f"   🚢 船舶: {data['ship_type']} @ {data['speed']}节")
                print(f"   ⛽ 预测油耗: {data['predicted_consumption']}mt")
                print(f"   📈 置信度: {data['confidence']}")
                print(f"   🔧 方法: {data['method']}")
                print(f"   📊 预测范围: {data['prediction_range'][0]}-{data['prediction_range'][1]}mt")
                return data
            else:
                print(f"   ❌ 预测失败: {response.status_code}")
                print(f"   错误: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def test_batch_prediction(self):
        """测试批量预测"""
        print("\n📦 测试批量预测...")
        
        batch_payload = {
            "predictions": [
                {
                    "ship_type": "Bulk Carrier",
                    "speed": 10.0,
                    "dwt": 50000,
                    "ship_age": 5
                },
                {
                    "ship_type": "Container Ship",
                    "speed": 20.0,
                    "dwt": 150000,
                    "ship_age": 10
                },
                {
                    "ship_type": "Crude Oil Tanker",
                    "speed": 14.0,
                    "dwt": 200000,
                    "ship_age": 15,
                    "load_condition": "Ballast"
                }
            ]
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/predict/batch",
                json=batch_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 批量预测成功")
                print(f"   📊 总请求数: {data['total_requests']}")
                print(f"   ✅ 成功预测: {data['successful_predictions']}")
                print(f"   ❌ 失败预测: {data['failed_predictions']}")
                
                print(f"   📋 预测结果:")
                for i, result in enumerate(data['results'][:3], 1):
                    if 'predicted_consumption' in result:
                        print(f"     {i}. {result['ship_type']} @ {result['speed']}节: {result['predicted_consumption']}mt")
                
                return data
            else:
                print(f"   ❌ 批量预测失败: {response.status_code}")
                print(f"   错误: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def test_load_comparison(self):
        """测试载重状态对比"""
        print("\n⚖️ 测试载重状态对比...")
        
        payload = {
            "ship_type": "Bulk Carrier",
            "speed": 12.0,
            "dwt": 75000,
            "ship_age": 10
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/analyze/load-comparison",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 载重状态对比成功")
                
                if 'comparison_results' in data:
                    for result in data['comparison_results']:
                        condition = "满载" if result['load_condition'] == 'Laden' else "压载"
                        print(f"   {condition}: {result['predicted_consumption']}mt")
                
                if 'consumption_difference' in data:
                    diff = data['consumption_difference']
                    print(f"   📊 差异: {diff['absolute']}mt ({diff['percentage']}%)")
                    print(f"   💡 建议: {data['recommendation']}")
                
                return data
            else:
                print(f"   ❌ 载重状态对比失败: {response.status_code}")
                print(f"   错误: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def test_ship_age_analysis(self):
        """测试船龄影响分析"""
        print("\n🚢 测试船龄影响分析...")
        
        params = {
            "ship_type": "Container Ship",
            "speed": 18.0,
            "dwt": 120000,
            "age_min": 0,
            "age_max": 20
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/analyze/ship-age",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 船龄分析成功")
                
                if 'most_efficient_age' in data:
                    best_age = data['most_efficient_age']
                    print(f"   🏆 最经济船龄: {best_age['ship_age']}年")
                    print(f"   ⛽ 对应油耗: {best_age['predicted_consumption']}mt")
                    print(f"   📊 效率范围: {data['efficiency_range']}mt")
                
                return data
            else:
                print(f"   ❌ 船龄分析失败: {response.status_code}")
                print(f"   错误: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def test_system_status(self):
        """测试系统状态"""
        print("\n📊 测试系统状态...")
        
        try:
            response = self.session.get(f"{self.base_url}/status")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 状态查询成功")
                print(f"   🔧 API版本: {data.get('api_version', 'N/A')}")
                print(f"   📊 模型状态: {'已加载' if data.get('model_loaded') else '未加载'}")
                print(f"   🚢 支持船型: {len(data.get('supported_ship_types', []))}种")
                return data
            else:
                print(f"   ❌ 状态查询失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def test_ship_types(self):
        """测试船舶类型列表"""
        print("\n🏷️ 测试船舶类型列表...")
        
        try:
            response = self.session.get(f"{self.base_url}/ship-types")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 船型列表获取成功")
                print(f"   📊 总计: {data['total_types']}种船型")
                
                print(f"   🚢 支持的船型:")
                for ship_type in data['ship_types'][:5]:  # 显示前5种
                    print(f"     • {ship_type['type']} ({ship_type['chinese']})")
                
                return data
            else:
                print(f"   ❌ 船型列表获取失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始FastAPI客户端测试")
        print("=" * 60)
        
        # 测试连接
        if not self.test_health():
            print("\n❌ 服务器连接失败，请确保API服务器正在运行")
            print("启动命令: python fastapi_server.py")
            return False
        
        # 运行各项测试
        tests = [
            self.test_basic_prediction_get,
            self.test_enhanced_prediction_post,
            self.test_batch_prediction,
            self.test_load_comparison,
            self.test_ship_age_analysis,
            self.test_system_status,
            self.test_ship_types
        ]
        
        success_count = 0
        for test in tests:
            try:
                result = test()
                if result is not None:
                    success_count += 1
            except Exception as e:
                print(f"   ❌ 测试异常: {e}")
        
        print(f"\n📊 测试总结:")
        print(f"   ✅ 成功: {success_count}/{len(tests)}")
        print(f"   📈 成功率: {success_count/len(tests)*100:.1f}%")
        
        if success_count == len(tests):
            print(f"   🎉 所有测试通过！")
        else:
            print(f"   ⚠️ 部分测试失败，请检查服务器状态")
        
        return success_count == len(tests)

def main():
    """主函数"""
    client = FuelPredictionClient()
    
    print("🚀 船舶油耗预测API客户端测试")
    print(f"🌐 服务器地址: {API_BASE_URL}")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = client.run_all_tests()
    
    if success:
        print(f"\n💡 使用提示:")
        print(f"   • API文档: {API_BASE_URL}/docs")
        print(f"   • 基础预测: GET {API_BASE_URL}/predict?ship_type=Bulk Carrier&speed=12.0")
        print(f"   • 增强预测: POST {API_BASE_URL}/predict (JSON数据)")
        print(f"   • 系统状态: GET {API_BASE_URL}/status")

if __name__ == "__main__":
    main()
