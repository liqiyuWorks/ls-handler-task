# 船舶坏天气航行性能计算功能

## 功能概述

本功能为船舶性能计算系统新增了坏天气条件下的航行性能分析，通过对比好天气和坏天气的船舶性能，为航运安全提供数据支持。

## 坏天气判断标准

### 主要判断条件

1. **风力等级判断**
   - 风力 ≥ 8级：大风天气（恶劣天气）
   - 风力 ≥ 6级：强风天气（恶劣天气）
   - 风力 ≥ 5级：清风天气（中等坏天气）

2. **浪高判断**
   - 浪高 ≥ 4.0米：大浪天气（恶劣天气）
   - 浪高 ≥ 2.5米：中浪天气（恶劣天气）
   - 浪高 ≥ 1.5米：小浪天气（中等坏天气）

3. **组合条件判断**
   - 风力 ≥ 5级 且 浪高 ≥ 1.5米：风浪组合天气（中等坏天气）

4. **航行状态验证**
   - 船速 ≥ 设计速度的30%（确保船舶在航行状态）

### 参考标准来源

- 国际海事组织(IMO)航行安全指南
- 中国海事局船舶航行安全规定
- 航运业实践经验
- 国际气象组织(WMO)标准

## 功能特性

### 1. 多层次天气分类

- **正常天气**：风力 < 5级 且 浪高 < 1.5米
- **中等坏天气**：风力 5-6级 或 浪高 1.5-2.5米
- **恶劣天气**：风力 ≥ 6级 或 浪高 ≥ 2.5米

### 2. 详细性能统计

- 总体坏天气性能
- 按载重状态分类（空载/满载）
- 按流向分类（顺流/逆流）
- 按天气严重程度分类（中等/恶劣）

### 3. 性能对比分析

- 好天气与坏天气速度对比
- 速度降低比例计算
- 载重状态性能影响分析
- 流向影响分析
- 设计速度达标率分析

### 4. 安全建议生成

- 基于性能分析的安全建议
- 操作洞察和建议
- 天气影响程度评估

## 输出数据格式

### 坏天气性能数据
```json
{
    "avg_bad_weather_speed": 12.5,
    "avg_downstream_bad_weather_speed": 13.2,
    "avg_non_downstream_bad_weather_speed": 11.8,
    "avg_severe_weather_speed": 10.5,
    "avg_moderate_bad_weather_speed": 14.2,
    "avg_ballast_bad_weather_speed": 13.1,
    "avg_laden_bad_weather_speed": 11.9
}
```

### 性能对比分析
```json
{
    "performance_comparison": {
        "good_weather_speed": 15.2,
        "bad_weather_speed": 12.5,
        "speed_reduction_percentage": 17.76,
        "speed_reduction_knots": 2.7
    },
    "speed_reduction_analysis": {
        "level": "moderate",
        "description": "中等速度降低"
    },
    "safety_recommendations": [
        "建议适当调整航速和航线"
    ],
    "operational_insights": [
        "船舶在恶劣天气下仍保持相对稳定的性能"
    ]
}
```

## 使用方法

### 1. 直接调用方法
```python
# 计算坏天气性能
bad_weather_perf = calc_vessel.deal_bad_perf_list(trace_data, draught, design_speed)

# 性能对比分析
analysis = calc_vessel.analyze_performance_comparison(
    good_weather_perf, bad_weather_perf, design_speed
)
```

### 2. 运行完整分析
```python
# 运行船舶性能分析（包含好天气和坏天气）
calc_vessel = CalcVesselPerformanceDetailsFromWmy()
calc_vessel.run()
```

## 安全建议

### 基于性能分析的建议

1. **严重速度降低（>30%）**
   - 建议在恶劣天气下考虑避风锚地
   - 加强天气监测和预警

2. **中等速度降低（15-30%）**
   - 建议适当调整航速和航线
   - 注意船舶稳定性

3. **轻微速度降低（<15%）**
   - 注意天气变化，保持正常航行
   - 定期检查船舶性能

### 操作建议

- 根据天气条件调整航行计划
- 加强船舶维护和性能监控
- 建立天气预警机制
- 定期分析船舶性能数据

## 技术实现

### 核心方法

1. `deal_bad_perf_list()`: 坏天气性能计算
2. `classify_weather_conditions()`: 天气条件分类
3. `analyze_performance_comparison()`: 性能对比分析

### 数据验证

- 风力等级范围：0-12级
- 浪高范围：0-10米
- 船速验证：确保船舶在航行状态
- 洋流数据验证：确保数据有效性

### 性能优化

- 使用累加器模式减少内存使用
- 改进数据验证逻辑
- 合并重复计算
- 提高代码可读性

## 注意事项

1. 确保轨迹数据包含完整的气象信息
2. 验证船舶设计参数的有效性
3. 定期更新天气判断标准
4. 结合实际情况调整性能阈值
5. 注意数据质量和完整性

## 扩展功能

未来可以考虑添加的功能：

1. 季节性天气影响分析
2. 不同船型的性能差异分析
3. 航线优化建议
4. 燃油消耗影响分析
5. 实时天气预警集成 