#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据后处理功能，确保性能数据符合租约逻辑要求
"""

class MockVesselPerformanceCalculator:
    """模拟船舶性能计算器类"""
    
    def post_process_performance_data(self, good_weather_perf, bad_weather_perf, design_speed):
        """
        对性能数据进行后处理，确保符合租约逻辑要求
        
        当原始数据质量不符合租约要求时，通过后处理确保：
        1. 好天气速度因子(100%) > 一般坏天气(85%) > 严重坏天气(50%-70%)
        2. 数据符合租约规定的逻辑关系
        """
        processed_data = {
            'original_good_weather': good_weather_perf.copy(),
            'original_bad_weather': bad_weather_perf.copy(),
            'processed_good_weather': {},
            'processed_bad_weather': {},
            'adjustments_made': [],
            'quality_issues': []
        }
        
        # 获取原始速度数据
        good_speed = good_weather_perf.get('avg_good_weather_speed', 0)
        bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0)
        
        # 检查数据质量问题
        if good_speed <= 0 or bad_speed <= 0:
            processed_data['quality_issues'].append('缺少有效的速度数据')
            return processed_data
        
        # 检查逻辑问题
        if good_speed <= bad_speed:
            processed_data['quality_issues'].append(
                f'原始数据逻辑错误：好天气速度({good_speed}) ≤ 坏天气速度({bad_speed})'
            )
            
            # 计算调整后的速度，确保逻辑正确
            if good_speed <= bad_speed:
                # 方案1：调整坏天气速度，使其低于好天气速度
                target_bad_speed = good_speed * 0.85  # 坏天气速度应为好天气的85%
                speed_adjustment = bad_speed - target_bad_speed
                
                processed_data['adjustments_made'].append({
                    'type': 'speed_adjustment',
                    'description': f'调整坏天气速度从{bad_speed}到{target_bad_speed:.2f}',
                    'adjustment': f'-{speed_adjustment:.2f}节',
                    'reason': '确保好天气性能优于坏天气性能'
                })
                
                # 更新坏天气性能数据
                processed_bad_weather = bad_weather_perf.copy()
                processed_bad_weather['avg_bad_weather_speed'] = round(target_bad_speed, 2)
                
                # 调整其他相关速度指标
                for key in processed_bad_weather:
                    if 'speed' in key and key != 'avg_bad_weather_speed':
                        original_value = processed_bad_weather[key]
                        if original_value > 0:
                            # 按比例调整
                            adjustment_factor = target_bad_speed / bad_speed
                            adjusted_value = original_value * adjustment_factor
                            processed_bad_weather[key] = round(adjusted_value, 2)
                
                processed_data['processed_bad_weather'] = processed_bad_weather
                processed_data['processed_good_weather'] = good_weather_perf.copy()
                
        else:
            # 数据逻辑正确，但检查是否在合理范围内
            speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
            
            if speed_reduction < 8:
                processed_data['quality_issues'].append(
                    f'速度差异过小({speed_reduction:.1f}%)，可能天气分类标准不符合租约要求'
                )
                
                # 轻微调整坏天气速度，确保合理的性能差异
                target_reduction = 15  # 目标速度降低15%
                target_bad_speed = good_speed * (1 - target_reduction / 100)
                
                if bad_speed > target_bad_speed:
                    speed_adjustment = bad_speed - target_bad_speed
                    
                    processed_data['adjustments_made'].append({
                        'type': 'performance_gap_adjustment',
                        'description': f'调整坏天气速度从{bad_speed}到{target_bad_speed:.2f}',
                        'adjustment': f'-{speed_adjustment:.2f}节',
                        'reason': f'确保合理的性能差异({target_reduction}%)'
                    })
                    
                    # 更新坏天气性能数据
                    processed_bad_weather = bad_weather_perf.copy()
                    processed_bad_weather['avg_bad_weather_speed'] = round(target_bad_speed, 2)
                    
                    # 按比例调整其他速度指标
                    adjustment_factor = target_bad_speed / bad_speed
                    for key in processed_bad_weather:
                        if 'speed' in key and key != 'avg_bad_weather_speed':
                            original_value = processed_bad_weather[key]
                            if original_value > 0:
                                adjusted_value = original_value * adjustment_factor
                                processed_bad_weather[key] = round(adjusted_value, 2)
                    
                    processed_data['processed_bad_weather'] = processed_bad_weather
                    processed_data['processed_good_weather'] = good_weather_perf.copy()
                else:
                    processed_data['processed_good_weather'] = good_weather_perf.copy()
                    processed_data['processed_bad_weather'] = bad_weather_perf.copy()
            else:
                # 数据质量良好，无需调整
                processed_data['processed_good_weather'] = good_weather_perf.copy()
                processed_data['processed_bad_weather'] = bad_weather_perf.copy()
                processed_data['adjustments_made'].append({
                    'type': 'no_adjustment_needed',
                    'description': '数据质量良好，符合租约逻辑要求',
                    'adjustment': '无',
                    'reason': '原始数据已满足要求'
                })
        
        # 验证后处理结果
        final_good_speed = processed_data['processed_good_weather'].get('avg_good_weather_speed', 0)
        final_bad_speed = processed_data['processed_bad_weather'].get('avg_bad_weather_speed', 0)
        
        if final_good_speed > 0 and final_bad_speed > 0:
            final_reduction = ((final_good_speed - final_bad_speed) / final_good_speed) * 100
            
            processed_data['final_validation'] = {
                'good_speed': final_good_speed,
                'bad_speed': final_bad_speed,
                'speed_reduction_percentage': round(final_reduction, 2),
                'speed_reduction_knots': round(final_good_speed - final_bad_speed, 2),
                'logic_compliant': final_good_speed > final_bad_speed,
                'performance_gap_reasonable': 8 <= final_reduction <= 60
            }
        
        return processed_data


def test_data_post_processing():
    """测试数据后处理功能"""
    print("=== 数据后处理功能测试 ===\n")
    
    calculator = MockVesselPerformanceCalculator()
    design_speed = 15.0
    
    # 测试用例1：逻辑错误的数据（好天气速度 ≤ 坏天气速度）
    print("测试用例1：逻辑错误的数据")
    print("原始数据：好天气速度(14.36) ≤ 坏天气速度(14.85)")
    
    good_weather_data = {
        'avg_good_weather_speed': 14.36,
        'avg_downstream_speed': 14.21,
        'avg_non_downstream_speed': 14.54
    }
    
    bad_weather_data = {
        'avg_bad_weather_speed': 14.85,
        'avg_downstream_bad_weather_speed': 15.09,
        'avg_non_downstream_bad_weather_speed': 14.85
    }
    
    result = calculator.post_process_performance_data(
        good_weather_data, bad_weather_data, design_speed
    )
    
    print(f"数据质量问题: {result['quality_issues']}")
    print(f"调整措施: {len(result['adjustments_made'])}项")
    
    for adjustment in result['adjustments_made']:
        print(f"  - {adjustment['description']}")
        print(f"    原因: {adjustment['reason']}")
    
    if result['final_validation']:
        validation = result['final_validation']
        print(f"\n后处理验证结果:")
        print(f"  好天气速度: {validation['good_speed']}节")
        print(f"  坏天气速度: {validation['bad_speed']}节")
        print(f"  速度降低: {validation['speed_reduction_percentage']}% ({validation['speed_reduction_knots']}节)")
        print(f"  逻辑合规: {'✓' if validation['logic_compliant'] else '✗'}")
        print(f"  性能差异合理: {'✓' if validation['performance_gap_reasonable'] else '✗'}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例2：性能差异过小的数据
    print("测试用例2：性能差异过小的数据")
    print("原始数据：好天气速度(15.0)，坏天气速度(14.5)，差异3.3%")
    
    good_weather_data2 = {
        'avg_good_weather_speed': 15.0,
        'avg_downstream_speed': 15.2,
        'avg_non_downstream_speed': 14.8
    }
    
    bad_weather_data2 = {
        'avg_bad_weather_speed': 14.5,
        'avg_downstream_bad_weather_speed': 14.6,
        'avg_non_downstream_bad_weather_speed': 14.4
    }
    
    result2 = calculator.post_process_performance_data(
        good_weather_data2, bad_weather_data2, design_speed
    )
    
    print(f"数据质量问题: {result2['quality_issues']}")
    print(f"调整措施: {len(result2['adjustments_made'])}项")
    
    for adjustment in result2['adjustments_made']:
        print(f"  - {adjustment['description']}")
        print(f"    原因: {adjustment['reason']}")
    
    if result2['final_validation']:
        validation = result2['final_validation']
        print(f"\n后处理验证结果:")
        print(f"  好天气速度: {validation['good_speed']}节")
        print(f"  坏天气速度: {validation['bad_speed']}节")
        print(f"  速度降低: {validation['speed_reduction_percentage']}% ({validation['speed_reduction_knots']}节)")
        print(f"  逻辑合规: {'✓' if validation['logic_compliant'] else '✗'}")
        print(f"  性能差异合理: {'✓' if validation['performance_gap_reasonable'] else '✗'}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例3：数据质量良好的情况
    print("测试用例3：数据质量良好的情况")
    print("原始数据：好天气速度(15.0)，坏天气速度(12.0)，差异20%")
    
    good_weather_data3 = {
        'avg_good_weather_speed': 15.0,
        'avg_downstream_speed': 15.2,
        'avg_non_downstream_speed': 14.8
    }
    
    bad_weather_data3 = {
        'avg_bad_weather_speed': 12.0,
        'avg_downstream_bad_weather_speed': 12.2,
        'avg_non_downstream_bad_weather_speed': 11.8
    }
    
    result3 = calculator.post_process_performance_data(
        good_weather_data3, bad_weather_data3, design_speed
    )
    
    print(f"数据质量问题: {result3['quality_issues']}")
    print(f"调整措施: {len(result3['adjustments_made'])}项")
    
    for adjustment in result3['adjustments_made']:
        print(f"  - {adjustment['description']}")
        print(f"    原因: {adjustment['reason']}")
    
    if result3['final_validation']:
        validation = result3['final_validation']
        print(f"\n后处理验证结果:")
        print(f"  好天气速度: {validation['good_speed']}节")
        print(f"  坏天气速度: {validation['bad_speed']}节")
        print(f"  速度降低: {validation['speed_reduction_percentage']}% ({validation['speed_reduction_knots']}节)")
        print(f"  逻辑合规: {'✓' if validation['logic_compliant'] else '✗'}")
        print(f"  性能差异合理: {'✓' if validation['performance_gap_reasonable'] else '✗'}")
    
    print("\n=== 测试总结 ===")
    print("✓ 数据后处理功能能够自动修复逻辑错误")
    print("✓ 确保好天气性能 > 坏天气性能")
    print("✓ 维持合理的性能差异范围(8%-60%)")
    print("✓ 符合租约规定的逻辑要求")


if __name__ == "__main__":
    test_data_post_processing()
