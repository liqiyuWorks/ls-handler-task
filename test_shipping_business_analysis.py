#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试航运业务分析功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 模拟船舶数据和性能数据
mock_vessel_data = {
    "mmsi": 123456789,
    "vesselTypeNameCn": "干散货",
    "draught": 12.5,
    "speed": 14.5,
    "buildYear": 2018,
    "length": 180,
    "width": 32,
    "dwt": 50000,
    "height": 15
}

mock_weather_performance = {
    "avg_good_weather_speed": 13.8,
    "avg_bad_weather_speed": 11.2,
    "avg_severe_weather_speed": 9.5,
    "avg_moderate_bad_weather_speed": 12.8,
    "avg_ballast_speed": 14.2,
    "avg_laden_speed": 12.5,
    "avg_downstream_speed": 14.0,
    "avg_non_downstream_speed": 12.8
}

def test_captain_assessment():
    """测试船长评估功能"""
    print("=== 测试船长评估功能 ===")
    
    # 模拟船长评估函数
    def assess_vessel_performance_from_captain_perspective(vessel_data, weather_performance, design_speed):
        assessment = {
            'captain_assessment': {},
            'operational_recommendations': [],
            'safety_considerations': [],
            'commercial_insights': [],
            'vessel_rating': {}
        }
        
        # 船舶基础信息
        vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
        length = vessel_data.get('length', 0)
        width = vessel_data.get('width', 0)
        dwt = vessel_data.get('dwt', 0)
        build_year = vessel_data.get('buildYear', 0)
        
        # 性能分析
        good_speed = weather_performance.get('avg_good_weather_speed', 0)
        bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
        
        # 1. 船舶操纵性能评估
        if good_speed > 0 and bad_speed > 0:
            speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
            
            if speed_reduction <= 10:
                assessment['vessel_rating']['weather_adaptability'] = 'excellent'
                assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下表现优异，具有良好的适航性'
            elif speed_reduction <= 20:
                assessment['vessel_rating']['weather_adaptability'] = 'good'
                assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下表现良好，适合大多数航线'
            elif speed_reduction <= 30:
                assessment['vessel_rating']['weather_adaptability'] = 'fair'
                assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下性能一般，需要谨慎选择航线'
            else:
                assessment['vessel_rating']['weather_adaptability'] = 'poor'
                assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下性能较差，建议避风航行'
        
        # 2. 燃油效率评估
        if good_speed > 0:
            # 基于船长经验的燃油消耗估算
            base_consumption = 20 if '干散货' in vessel_type else 18
            dwt_factor = min(dwt / 50000, 2.0)
            speed_factor = (good_speed / 14.0) ** 3
            fuel_good = base_consumption * dwt_factor * speed_factor
            
            speed_factor_bad = (bad_speed / 14.0) ** 3 if bad_speed > 0 else speed_factor
            fuel_bad = base_consumption * dwt_factor * speed_factor_bad
            
            assessment['captain_assessment']['fuel_efficiency'] = {
                'good_weather_consumption': round(fuel_good, 2),
                'bad_weather_consumption': round(fuel_bad, 2),
                'consumption_increase': round(((fuel_bad - fuel_good) / fuel_good) * 100, 2) if fuel_good > 0 else 0
            }
        
        # 3. 船舶稳定性评估
        if length > 0 and width > 0:
            length_width_ratio = length / width
            if length_width_ratio > 7:
                assessment['safety_considerations'].append('长宽比较大，在恶劣天气下可能影响稳定性')
            elif length_width_ratio < 5:
                assessment['safety_considerations'].append('长宽比较小，稳定性较好')
            else:
                assessment['safety_considerations'].append('长宽比适中，稳定性良好')
        
        # 4. 商业洞察
        current_year = 2024
        vessel_age = current_year - build_year if build_year > 0 else 0
        
        if vessel_age < 10:
            assessment['commercial_insights'].append('船舶较新，在恶劣天气下应有良好表现')
        elif vessel_age > 20:
            assessment['commercial_insights'].append('船舶年龄较大，可能影响在恶劣天气下的性能表现')
        
        if good_speed > 0 and design_speed > 0:
            performance_ratio = (good_speed / design_speed) * 100
            if performance_ratio > 95:
                assessment['commercial_insights'].append('船舶性能优异，具有较高的商业价值')
            elif performance_ratio < 80:
                assessment['commercial_insights'].append('船舶实际性能低于设计标准，可能影响商业价值')
        
        return assessment
    
    # 执行测试
    design_speed = mock_vessel_data.get('speed', 14.5)
    assessment = assess_vessel_performance_from_captain_perspective(
        mock_vessel_data, mock_weather_performance, design_speed
    )
    
    print("船长评估结果:")
    print(f"  天气适应性评级: {assessment['vessel_rating'].get('weather_adaptability', 'N/A')}")
    print(f"  天气操纵性能: {assessment['captain_assessment'].get('weather_handling', 'N/A')}")
    
    if 'fuel_efficiency' in assessment['captain_assessment']:
        fuel_info = assessment['captain_assessment']['fuel_efficiency']
        print(f"  燃油消耗分析:")
        print(f"    好天气消耗: {fuel_info['good_weather_consumption']} 吨/天")
        print(f"    坏天气消耗: {fuel_info['bad_weather_consumption']} 吨/天")
        print(f"    消耗增加: {fuel_info['consumption_increase']}%")
    
    print(f"  安全考虑: {assessment['safety_considerations']}")
    print(f"  商业洞察: {assessment['commercial_insights']}")
    print()

def test_trading_analysis():
    """测试买卖船分析功能"""
    print("=== 测试买卖船分析功能 ===")
    
    def analyze_vessel_for_trading(vessel_data, weather_performance, design_speed):
        analysis = {
            'vessel_value': {},
            'investment_potential': {},
            'resale_considerations': [],
            'buying_recommendations': []
        }
        
        vessel_type = vessel_data.get('vesselTypeNameCn', '')
        build_year = vessel_data.get('buildYear', 0)
        dwt = vessel_data.get('dwt', 0)
        good_speed = weather_performance.get('avg_good_weather_speed', 0)
        bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
        
        # 船舶价值评估
        current_year = 2024
        vessel_age = current_year - build_year if build_year > 0 else 0
        
        # 基于年龄的价值评估
        if vessel_age <= 5:
            age_factor = 1.0
            analysis['vessel_value']['age_rating'] = 'excellent'
        elif vessel_age <= 10:
            age_factor = 0.9
            analysis['vessel_value']['age_rating'] = 'good'
        elif vessel_age <= 15:
            age_factor = 0.8
            analysis['vessel_value']['age_rating'] = 'fair'
        else:
            age_factor = 0.6
            analysis['vessel_value']['age_rating'] = 'poor'
        
        # 基于性能的价值评估
        if good_speed > 0 and design_speed > 0:
            performance_factor = min(good_speed / design_speed, 1.2)
        else:
            performance_factor = 0.8
        
        # 天气适应性价值
        if good_speed > 0 and bad_speed > 0:
            weather_factor = (bad_speed / good_speed) * 1.2
        else:
            weather_factor = 1.0
        
        # 综合价值评估
        total_value_factor = age_factor * performance_factor * weather_factor
        analysis['vessel_value']['total_value_factor'] = round(total_value_factor, 3)
        
        # 投资潜力评估
        if total_value_factor >= 1.0:
            analysis['investment_potential']['rating'] = 'high'
            analysis['investment_potential']['description'] = '船舶具有较高的投资价值'
        elif total_value_factor >= 0.8:
            analysis['investment_potential']['rating'] = 'medium'
            analysis['investment_potential']['description'] = '船舶具有中等投资价值'
        else:
            analysis['investment_potential']['rating'] = 'low'
            analysis['investment_potential']['description'] = '船舶投资价值较低'
        
        # 购买建议
        if total_value_factor >= 1.0 and weather_factor >= 0.8:
            analysis['buying_recommendations'].append('强烈推荐购买，船舶性能优异且天气适应性良好')
        elif total_value_factor >= 0.8:
            analysis['buying_recommendations'].append('建议购买，但需要关注天气适应性')
        else:
            analysis['buying_recommendations'].append('谨慎考虑，建议进一步评估')
        
        return analysis
    
    # 执行测试
    design_speed = mock_vessel_data.get('speed', 14.5)
    trading_analysis = analyze_vessel_for_trading(
        mock_vessel_data, mock_weather_performance, design_speed
    )
    
    print("买卖船分析结果:")
    print(f"  年龄评级: {trading_analysis['vessel_value']['age_rating']}")
    print(f"  综合价值因子: {trading_analysis['vessel_value']['total_value_factor']}")
    print(f"  投资潜力: {trading_analysis['investment_potential']['rating']}")
    print(f"  投资描述: {trading_analysis['investment_potential']['description']}")
    print(f"  购买建议: {trading_analysis['buying_recommendations']}")
    print()

def test_chartering_analysis():
    """测试租船分析功能"""
    print("=== 测试租船分析功能 ===")
    
    def analyze_vessel_for_chartering(vessel_data, weather_performance, design_speed):
        analysis = {
            'charter_potential': {},
            'operational_efficiency': {},
            'charter_recommendations': [],
            'rate_considerations': []
        }
        
        vessel_type = vessel_data.get('vesselTypeNameCn', '')
        dwt = vessel_data.get('dwt', 0)
        good_speed = weather_performance.get('avg_good_weather_speed', 0)
        bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
        
        # 租船潜力评估
        if good_speed > 0 and bad_speed > 0:
            weather_adaptability = (bad_speed / good_speed) * 100
            
            if weather_adaptability >= 85:
                analysis['charter_potential']['rating'] = 'excellent'
                analysis['charter_potential']['description'] = '船舶天气适应性极佳，适合全年租船'
            elif weather_adaptability >= 70:
                analysis['charter_potential']['rating'] = 'good'
                analysis['charter_potential']['description'] = '船舶天气适应性良好，适合大部分航线'
            elif weather_adaptability >= 50:
                analysis['charter_potential']['rating'] = 'fair'
                analysis['charter_potential']['description'] = '船舶天气适应性一般，需要谨慎选择航线'
            else:
                analysis['charter_potential']['rating'] = 'poor'
                analysis['charter_potential']['description'] = '船舶天气适应性较差，租船风险较高'
        
        # 运营效率评估
        if good_speed > 0:
            operational_days_good = 365 * 0.85
            operational_days_bad = 365 * 0.15
            
            total_distance_good = good_speed * 24 * operational_days_good
            total_distance_bad = bad_speed * 24 * operational_days_bad
            total_distance = total_distance_good + total_distance_bad
            
            analysis['operational_efficiency']['annual_distance'] = round(total_distance, 0)
            analysis['operational_efficiency']['average_speed'] = round(total_distance / (365 * 24), 2)
        
        # 租船建议
        if analysis['charter_potential']['rating'] in ['excellent', 'good']:
            analysis['charter_recommendations'].append('船舶适合长期租船，具有稳定的收益潜力')
        elif analysis['charter_potential']['rating'] == 'fair':
            analysis['charter_recommendations'].append('船舶适合短期租船，需要仔细选择航线')
        else:
            analysis['charter_recommendations'].append('船舶租船风险较高，建议谨慎考虑')
        
        # 租金考虑
        if analysis['charter_potential']['rating'] == 'excellent':
            analysis['rate_considerations'].append('船舶性能优异，可以要求较高的租金')
        elif analysis['charter_potential']['rating'] == 'good':
            analysis['rate_considerations'].append('船舶性能良好，租金可以略高于市场平均水平')
        elif analysis['charter_potential']['rating'] == 'fair':
            analysis['rate_considerations'].append('船舶性能一般，租金应与市场平均水平相当')
        else:
            analysis['rate_considerations'].append('船舶性能较差，租金应低于市场平均水平以吸引租船人')
        
        return analysis
    
    # 执行测试
    design_speed = mock_vessel_data.get('speed', 14.5)
    chartering_analysis = analyze_vessel_for_chartering(
        mock_vessel_data, mock_weather_performance, design_speed
    )
    
    print("租船分析结果:")
    print(f"  租船潜力评级: {chartering_analysis['charter_potential']['rating']}")
    print(f"  租船潜力描述: {chartering_analysis['charter_potential']['description']}")
    print(f"  年度航程: {chartering_analysis['operational_efficiency']['annual_distance']} 海里")
    print(f"  平均速度: {chartering_analysis['operational_efficiency']['average_speed']} 节")
    print(f"  租船建议: {chartering_analysis['charter_recommendations']}")
    print(f"  租金考虑: {chartering_analysis['rate_considerations']}")
    print()

def main():
    """主测试函数"""
    print("开始测试航运业务分析功能...\n")
    
    try:
        test_captain_assessment()
        test_trading_analysis()
        test_chartering_analysis()
        print("所有测试完成！")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 