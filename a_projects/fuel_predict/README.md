# 船舶油耗预测系统 V3.0 - 简化版

## 🎯 项目概述

本项目是基于NOON报告数据的高精度船舶油耗预测系统V3.0简化版，仅保留核心功能模块，包括V3模型训练、评估和API服务。

### 🚀 核心功能
- ✅ **V3模型训练**: 基于相关性分析的高精度预测模型
- ✅ **模型评估**: 完整的模型性能评估和验证
- ✅ **FastAPI服务**: RESTful API接口和Swagger文档
- ✅ **多维度预测**: 支持12个输入特征的增强预测

### 📊 技术指标
- **预测精度**: R² = 0.8677, MAE < 1.0mt
- **数据基础**: 35,289条NOON报告数据
- **支持船型**: 7种主要商船类型
- **API响应**: < 100ms响应时间

## 📁 简化项目结构

```
fuel_predict_v3_simplified/
├── api/                                # API模块
│   ├── enhanced_fuel_predictor_v3.py   # V3模型训练和评估
│   ├── enhanced_fuel_api_v3.py         # V3 API核心
│   ├── data_processor_enhanced.py      # 数据处理器
│   ├── fastapi_server.py               # FastAPI服务器
│   └── test_api_client.py              # API测试客户端
├── data/                               # 数据文件
│   ├── processed_noon_data.csv         # 处理后训练数据
│   └── ship_speed_summary.csv          # 船舶-速度汇总
├── models/                             # 训练好的模型
│   └── enhanced_fuel_model_v3_*.pkl    # V3预测模型
├── docs/                               # 核心文档
├── examples/                           # 使用示例
├── README.md                           # 项目说明
└── requirements.txt                    # 依赖列表
```

## 🚀 快速开始

### 1. 环境安装
```bash
pip install -r requirements.txt
```

### 2. 启动API服务
```bash
cd api/
python fastapi_server.py
```

### 3. 访问服务
- **Swagger文档**: http://localhost:8080/docs
- **服务首页**: http://localhost:8080
- **健康检查**: http://localhost:8080/health

### 4. 模型训练 (可选)
```bash
cd api/
python enhanced_fuel_predictor_v3.py
```

## 🔧 核心模块说明

### 1. enhanced_fuel_predictor_v3.py
- **功能**: V3模型训练和评估
- **特点**: 基于相关性分析的特征选择
- **输出**: 训练好的V3模型文件

### 2. enhanced_fuel_api_v3.py  
- **功能**: V3 API核心预测逻辑
- **特点**: 支持12个输入特征的多维度预测
- **接口**: 完整的预测和分析功能

### 3. fastapi_server.py
- **功能**: FastAPI Web服务器
- **特点**: RESTful API + Swagger自动文档
- **端口**: 8080 (可配置)

### 4. data_processor_enhanced.py
- **功能**: 增强数据处理器
- **特点**: NOON报告数据筛选和特征工程
- **输出**: 处理后的训练数据

## 📡 API接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/predict` | GET/POST | 油耗预测 |
| `/predict/batch` | POST | 批量预测 |
| `/analyze/load-comparison` | POST | 载重状态对比 |
| `/analyze/ship-age` | POST | 船龄影响分析 |
| `/status` | GET | 系统状态 |
| `/ship-types` | GET | 船型列表 |
| `/docs` | GET | Swagger文档 |

## 💡 使用示例

### Python调用
```python
import requests

# 基础预测
response = requests.get("http://localhost:8080/predict", params={
    "ship_type": "Bulk Carrier",
    "speed": 12.0,
    "dwt": 75000
})
result = response.json()
print(f"预测油耗: {result['predicted_consumption']}mt")
```

### cURL调用
```bash
# 基础预测
curl "http://localhost:8080/predict?ship_type=Bulk Carrier&speed=12.0"

# 增强预测
curl -X POST "http://localhost:8080/predict" \
  -H "Content-Type: application/json" \
  -d '{"ship_type": "Container Ship", "speed": 18.0, "dwt": 120000, "ship_age": 5}'
```

## 📞 技术支持

如需技术支持或功能扩展，请联系开发团队。

---

**版本**: V3.0 简化版  
**更新时间**: 2025-09-21  
**开发团队**: 船舶油耗预测系统开发组
