# 船舶油耗预测系统 V3.0 - 简化版

## 🎯 项目概述

基于NOON报告数据的高精度船舶油耗预测系统V3.0简化版，专门针对多维度特征输入进行优化。

### 核心特性
- ✅ **高精度预测**: R² = 0.8677，基于35,289条NOON报告数据
- ✅ **多维度输入**: 支持12个输入特征 (船龄、载重状态等)
- ✅ **FastAPI服务**: 完整的RESTful API接口
- ✅ **智能分析**: 特征影响分析、优化建议

## 📁 项目结构

```
fuel_predict_v3_clean/
├── api/                                # API和核心模块
│   ├── enhanced_fuel_predictor_v3.py   # V3.0预测模型
│   ├── enhanced_fuel_api_v3.py         # V3.0 API接口
│   ├── data_processor_enhanced.py      # 数据处理器
│   ├── fastapi_server.py               # FastAPI服务器
│   └── test_api_client.py              # API测试客户端
├── data/                               # 数据文件
│   ├── processed_noon_data.csv         # 处理后数据 (35,289条)
│   └── ship_speed_summary.csv          # 船舶-速度汇总
├── models/                             # 预测模型
│   └── enhanced_fuel_model_v3_*.pkl    # V3.0预测模型
├── docs/                               # 文档
│   ├── API_使用说明.md                  # API使用文档
│   └── 模型优化完成报告_V3.md           # 技术报告
├── start_api.sh                        # API启动脚本
├── requirements.txt                    # 依赖列表
└── README.md                           # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动FastAPI服务器
```bash
# 使用启动脚本 (推荐)
./start_api.sh

# 或直接运行
python api/fastapi_server.py
```

### 3. 访问API文档
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **服务首页**: http://localhost:8000

### 4. 测试API功能
```bash
# 运行测试客户端
python api/test_api_client.py

# 基础预测测试
curl "http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0&dwt=75000"
```

## 📊 支持的输入特征

### 必需参数
- `ship_type`: 船舶类型
- `speed`: 航行速度 (节)

### 可选参数 (V3.0增强)
- `dwt`: 载重吨
- `ship_age`: 船龄 (年)
- `load_condition`: 载重状态 (Laden/Ballast)
- `draft`: 船舶吃水 (米)
- `length`: 船舶总长度 (米)
- `latitude`, `longitude`: 地理位置
- `heavy_fuel_cp`, `light_fuel_cp`, `speed_cp`: 租约条款

## 🔧 API接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/predict` | GET/POST | 基础/增强预测 |
| `/predict/batch` | POST | 批量预测 |
| `/analyze/load-comparison` | POST | 载重状态对比 |
| `/analyze/ship-age` | POST | 船龄影响分析 |
| `/status` | GET | 系统状态 |
| `/ship-types` | GET | 船型列表 |

## 🚢 支持的船舶类型

- Bulk Carrier (散货船)
- Container Ship (集装箱船)
- Crude Oil Tanker (原油船)
- Chemical Tanker (化学品船)
- General Cargo (杂货船)
- Open Hatch Cargo (开舱杂货船)
- Other (其他类型)

## 📈 模型性能

| 指标 | 数值 |
|------|------|
| 决定系数 (R²) | 0.8677 |
| 平均绝对误差 (MAE) | 0.876 mt |
| 均方根误差 (RMSE) | 1.686 mt |
| 数据量 | 35,289条NOON报告 |

## 💡 使用示例

### Python调用
```python
import requests

# 基础预测
response = requests.get("http://localhost:8000/predict", params={
    "ship_type": "Bulk Carrier",
    "speed": 12.0,
    "dwt": 75000
})
result = response.json()
print(f"预测油耗: {result['predicted_consumption']}mt")

# 增强预测
response = requests.post("http://localhost:8000/predict", json={
    "ship_type": "Container Ship",
    "speed": 18.0,
    "dwt": 120000,
    "ship_age": 5,
    "load_condition": "Laden"
})
result = response.json()
```

### JavaScript调用
```javascript
// 基础预测
fetch('http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0')
  .then(response => response.json())
  .then(data => console.log(`预测油耗: ${data.predicted_consumption}mt`));
```

---

**版本**: V3.0 简化版  
**更新时间**: 2025-09-21  
**开发团队**: 船舶油耗预测系统开发组
