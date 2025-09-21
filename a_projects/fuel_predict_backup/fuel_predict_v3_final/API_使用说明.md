# 船舶油耗预测FastAPI使用说明

## 🎯 API概述

本API基于V3.0增强版船舶油耗预测系统，提供高精度的船舶燃油消耗预测服务。支持多维度特征输入和实时预测。

### 核心特性
- ✅ **高精度预测**: 基于35,289条NOON报告数据训练，R² = 0.8677
- ✅ **多维度输入**: 支持12个输入特征 (3个必需 + 9个可选)
- ✅ **RESTful API**: 标准的HTTP接口，支持GET和POST请求
- ✅ **自动文档**: 内置Swagger和ReDoc文档
- ✅ **批量处理**: 支持批量预测和分析功能

## 🚀 快速开始

### 1. 启动服务器

```bash
# 方式1: 使用启动脚本
./start_api.sh

# 方式2: 直接运行
python fastapi_server.py

# 方式3: 使用uvicorn
uvicorn fastapi_server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 访问API文档

- **服务地址**: http://localhost:8000
- **Swagger文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc

### 3. 健康检查

```bash
curl http://localhost:8000/health
```

## 📡 API接口详解

### 1. 基础预测 (GET方式)

**接口**: `GET /predict`

**描述**: 使用查询参数进行基础油耗预测

**必需参数**:
- `ship_type`: 船舶类型
- `speed`: 航行速度 (节)

**可选参数**:
- `dwt`: 载重吨
- `ship_age`: 船龄 (年)
- `load_condition`: 载重状态 (Laden/Ballast)

**示例**:
```bash
# 基础预测
curl "http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0"

# 带可选参数
curl "http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0&dwt=75000&ship_age=8&load_condition=Laden"
```

**响应示例**:
```json
{
  "predicted_consumption": 30.08,
  "confidence": "High",
  "method": "ml_model",
  "ship_type": "Bulk Carrier",
  "speed": 12.0,
  "prediction_range": [27.07, 33.09],
  "prediction_time": "2025-09-21T16:30:00",
  "api_version": "3.0"
}
```

### 2. 增强预测 (POST方式)

**接口**: `POST /predict`

**描述**: 使用JSON请求体进行多维度增强预测

**请求体示例**:
```json
{
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
  "light_fuel_cp": 850,
  "speed_cp": 18.0
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "ship_type": "Container Ship",
    "speed": 18.0,
    "dwt": 120000,
    "ship_age": 5,
    "load_condition": "Laden",
    "draft": 14.0,
    "length": 350
  }'
```

### 3. 批量预测

**接口**: `POST /predict/batch`

**描述**: 批量处理多个预测请求

**请求体示例**:
```json
{
  "predictions": [
    {
      "ship_type": "Bulk Carrier",
      "speed": 10.0,
      "dwt": 50000
    },
    {
      "ship_type": "Container Ship",
      "speed": 20.0,
      "dwt": 150000,
      "ship_age": 10
    }
  ]
}
```

### 4. 载重状态对比分析

**接口**: `POST /analyze/load-comparison`

**描述**: 对比满载和压载状态下的油耗差异

**请求体示例**:
```json
{
  "ship_type": "Bulk Carrier",
  "speed": 12.0,
  "dwt": 75000,
  "ship_age": 10
}
```

### 5. 船龄影响分析

**接口**: `POST /analyze/ship-age`

**描述**: 分析不同船龄对油耗的影响

**查询参数**:
- `ship_type`: 船舶类型
- `speed`: 航行速度
- `dwt`: 载重吨 (可选)
- `age_min`: 最小船龄 (默认0)
- `age_max`: 最大船龄 (默认25)

**示例**:
```bash
curl -X POST "http://localhost:8000/analyze/ship-age?ship_type=Container Ship&speed=18.0&dwt=120000&age_min=0&age_max=20"
```

### 6. 系统状态查询

**接口**: `GET /status`

**描述**: 获取API系统状态和配置信息

```bash
curl http://localhost:8000/status
```

### 7. 支持的船舶类型

**接口**: `GET /ship-types`

**描述**: 获取系统支持的船舶类型列表

```bash
curl http://localhost:8000/ship-types
```

## 🚢 支持的船舶类型

| 类型 | 英文名称 | 中文名称 | 描述 |
|------|----------|----------|------|
| Bulk Carrier | Bulk Carrier | 散货船 | 运输散装货物的船舶 |
| Container Ship | Container Ship | 集装箱船 | 运输集装箱的专用船舶 |
| Crude Oil Tanker | Crude Oil Tanker | 原油船 | 运输原油的油轮 |
| Chemical Tanker | Chemical Tanker | 化学品船 | 运输化学品的专用船舶 |
| General Cargo | General Cargo | 杂货船 | 运输各类杂货的船舶 |
| Open Hatch Cargo | Open Hatch Cargo | 开舱杂货船 | 具有可开启舱盖的杂货船 |
| Other | Other | 其他类型 | 其他类型的船舶 |

## 🔧 输入参数详解

### 必需参数

| 参数 | 类型 | 范围 | 描述 | 示例 |
|------|------|------|------|------|
| ship_type | string | - | 船舶类型 | "Bulk Carrier" |
| speed | float | 0-30 | 航行速度 (节) | 12.0 |

### 可选参数

| 参数 | 类型 | 范围 | 描述 | 示例 |
|------|------|------|------|------|
| dwt | float | 1000+ | 载重吨 | 75000 |
| ship_age | float | 0-50 | 船龄 (年) | 8 |
| load_condition | string | Laden/Ballast | 载重状态 | "Laden" |
| draft | float | 1-25 | 船舶吃水 (米) | 12.5 |
| length | float | 50-500 | 船舶总长度 (米) | 225 |
| latitude | float | -90 to 90 | 纬度 | 35.0 |
| longitude | float | -180 to 180 | 经度 | 139.0 |
| heavy_fuel_cp | float | 200-1500 | 重油CP价格 ($/吨) | 650 |
| light_fuel_cp | float | 300-2000 | 轻油CP价格 ($/吨) | 850 |
| speed_cp | float | 5-30 | 航速CP (节) | 12.0 |

## 📊 响应格式

### 预测响应

```json
{
  "predicted_consumption": 30.08,     // 预测油耗 (mt)
  "confidence": "High",               // 置信度 (High/Medium/Low)
  "method": "ml_model",               // 预测方法
  "ship_type": "Bulk Carrier",       // 船舶类型
  "speed": 12.0,                      // 航行速度
  "prediction_range": [27.07, 33.09], // 预测范围
  "prediction_time": "2025-09-21T16:30:00", // 预测时间
  "api_version": "3.0"                // API版本
}
```

### 错误响应

```json
{
  "detail": "预测失败: 错误描述"
}
```

## 🧪 测试客户端

系统提供了完整的测试客户端，可以测试所有API功能：

```bash
# 运行测试客户端
python test_api_client.py
```

测试客户端将自动测试：
- ✅ 健康检查
- ✅ 基础预测 (GET)
- ✅ 增强预测 (POST)
- ✅ 批量预测
- ✅ 载重状态对比
- ✅ 船龄影响分析
- ✅ 系统状态查询
- ✅ 船舶类型列表

## 💡 使用建议

### 1. 参数输入优先级

**高影响参数** (建议提供):
- 船舶类型 (必需)
- 航行速度 (必需)
- 载重吨 (dwt)
- 船舶尺寸 (draft, length)
- 重油CP价格

**辅助参数** (可选):
- 船龄
- 载重状态
- 地理位置
- 其他CP条款

### 2. 应用场景

**快速估算**:
```bash
curl "http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0"
```

**高精度预测**:
```json
{
  "ship_type": "Bulk Carrier",
  "speed": 12.0,
  "dwt": 75000,
  "ship_age": 8,
  "load_condition": "Laden",
  "draft": 12.5,
  "length": 225,
  "heavy_fuel_cp": 650
}
```

**批量分析**:
- 使用批量预测接口处理多个船舶
- 使用分析接口进行对比研究

### 3. 性能优化

- **单次预测**: 响应时间 < 100ms
- **批量预测**: 支持同时处理多个请求
- **缓存**: 相同参数的重复请求会被缓存

## 🔒 错误处理

### HTTP状态码

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 接口不存在
- `500`: 服务器内部错误
- `503`: 服务不可用 (预测器未初始化)

### 常见错误

1. **预测器未初始化** (503):
   - 检查模型文件是否存在
   - 重启服务器

2. **参数验证失败** (400):
   - 检查参数类型和范围
   - 参考参数说明

3. **预测失败** (500):
   - 检查输入参数的合理性
   - 查看服务器日志

## 📞 技术支持

如需技术支持或功能扩展，请联系开发团队。

---

**API版本**: V3.0  
**更新时间**: 2025-09-21  
**开发团队**: 船舶油耗预测系统开发组
