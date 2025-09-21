# -*- coding: utf-8 -*-
"""
船舶油耗预测FastAPI服务器
Ship Fuel Consumption Prediction FastAPI Server

基于V3.0增强版本的高精度预测API
支持多维度特征输入和实时预测服务

作者: 船舶油耗预测系统
日期: 2025-09-21
版本: 3.0
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import sys
import os
from datetime import datetime

# 添加当前目录到路径 (API模块在同一目录)
sys.path.append(os.path.dirname(__file__))

try:
    from enhanced_fuel_api_v3 import EnhancedFuelAPIV3
except ImportError as e:
    print(f"❌ 无法导入预测模型: {e}")
    print("请确保核心模块文件存在于 core/ 目录中")
    sys.exit(1)

# 创建FastAPI应用
app = FastAPI(
    title="船舶油耗预测API V3.0",
    description="基于NOON报告数据的高精度船舶油耗预测系统，支持多维度特征输入",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 全局预测器实例
predictor_api = None

# 数据模型定义
class PredictionRequest(BaseModel):
    """预测请求模型"""
    ship_type: str = Field(..., description="船舶类型", example="Bulk Carrier")
    speed: float = Field(..., ge=0, le=30, description="航行速度 (节)", example=12.0)
    dwt: Optional[float] = Field(None, ge=1000, description="载重吨", example=75000)
    ship_age: Optional[float] = Field(None, ge=0, le=50, description="船龄 (年)", example=8)
    load_condition: Optional[str] = Field("Laden", description="载重状态", example="Laden")
    draft: Optional[float] = Field(None, ge=1, le=25, description="船舶吃水 (米)", example=12.5)
    length: Optional[float] = Field(None, ge=50, le=500, description="船舶总长度 (米)", example=225)
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度", example=35.0)
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度", example=139.0)
    heavy_fuel_cp: Optional[float] = Field(None, ge=200, le=1500, description="重油CP价格 ($/吨)", example=650)
    light_fuel_cp: Optional[float] = Field(None, ge=300, le=2000, description="轻油CP价格 ($/吨)", example=850)
    speed_cp: Optional[float] = Field(None, ge=5, le=30, description="航速CP (节)", example=12.0)

    class Config:
        schema_extra = {
            "example": {
                "ship_type": "Bulk Carrier",
                "speed": 12.0,
                "dwt": 75000,
                "ship_age": 8,
                "load_condition": "Laden",
                "draft": 12.5,
                "length": 225,
                "latitude": 35.0,
                "longitude": 139.0,
                "heavy_fuel_cp": 650
            }
        }

class PredictionResponse(BaseModel):
    """预测响应模型"""
    predicted_consumption: float = Field(..., description="预测油耗 (mt)")
    confidence: str = Field(..., description="预测置信度")
    method: str = Field(..., description="预测方法")
    ship_type: str = Field(..., description="船舶类型")
    speed: float = Field(..., description="航行速度")
    prediction_range: tuple = Field(..., description="预测范围")
    prediction_time: str = Field(..., description="预测时间")
    api_version: str = Field(..., description="API版本")

class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""
    predictions: List[PredictionRequest] = Field(..., description="预测请求列表")

class LoadComparisonRequest(BaseModel):
    """载重状态对比请求模型"""
    ship_type: str = Field(..., description="船舶类型")
    speed: float = Field(..., ge=0, le=30, description="航行速度 (节)")
    dwt: Optional[float] = Field(None, ge=1000, description="载重吨")
    ship_age: Optional[float] = Field(None, ge=0, le=50, description="船龄 (年)")

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化预测器"""
    global predictor_api
    try:
        print("🚀 正在初始化船舶油耗预测系统...")
        predictor_api = EnhancedFuelAPIV3()
        
        if predictor_api:
            try:
                status = predictor_api.get_api_status_v3()
                if status.get('model_loaded', False):
                    print("✅ 预测模型加载成功")
                else:
                    print("⚠️ 预测模型未加载，使用增强规则模式")
                
                print(f"📊 支持的船舶类型: {len(status.get('supported_ship_types', []))}种")
                print(f"🔧 支持的特征数: {len(status.get('enhanced_features', {}).get('optional', []))}个")
            except Exception as status_error:
                print(f"⚠️ 状态查询失败: {status_error}")
        
        print("✅ API服务器初始化完成")
        
    except Exception as e:
        print(f"❌ 预测器初始化失败: {e}")
        print("⚠️ 将使用备用模式运行")
        predictor_api = None

# 根路径 - 欢迎页面
@app.get("/", response_class=HTMLResponse)
async def root():
    """API欢迎页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>船舶油耗预测API V3.0</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; }
            .feature { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .endpoint { background: #e8f6f3; padding: 10px; margin: 5px 0; border-left: 4px solid #27ae60; }
            a { color: #3498db; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .status.success { background: #d5edda; border: 1px solid #c3e6cb; color: #155724; }
            .status.warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚢 船舶油耗预测API V3.0</h1>
            
            <div class="status success">
                <strong>✅ 系统状态:</strong> 运行正常<br>
                <strong>📅 版本:</strong> V3.0 增强版<br>
                <strong>⏰ 启动时间:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
            </div>

            <h2>🎯 核心功能</h2>
            <div class="feature">
                <strong>多维度预测:</strong> 支持12个输入特征，包括船舶类型、速度、载重吨、船龄、载重状态、船舶尺寸、地理位置、租约条款等
            </div>
            <div class="feature">
                <strong>高精度模型:</strong> 基于35,289条NOON报告数据训练的集成学习模型 (R² = 0.8677)
            </div>
            <div class="feature">
                <strong>智能分析:</strong> 提供特征影响分析、载重状态对比、优化建议等功能
            </div>

            <h2>📡 API接口</h2>
            <div class="endpoint">
                <strong>GET /predict</strong> - 基础预测 (查询参数)
            </div>
            <div class="endpoint">
                <strong>POST /predict</strong> - 增强预测 (JSON请求体)
            </div>
            <div class="endpoint">
                <strong>POST /predict/batch</strong> - 批量预测
            </div>
            <div class="endpoint">
                <strong>POST /analyze/load-comparison</strong> - 载重状态对比分析
            </div>
            <div class="endpoint">
                <strong>GET /status</strong> - 系统状态查询
            </div>
            <div class="endpoint">
                <strong>GET /ship-types</strong> - 支持的船舶类型列表
            </div>

            <h2>📚 API文档</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <p><strong>📖 Swagger UI:</strong> <a href="/docs" target="_blank">http://localhost:8080/docs</a></p>
                <p><strong>📋 ReDoc:</strong> <a href="/redoc" target="_blank">http://localhost:8080/redoc</a></p>
                <p><em>推荐使用Swagger UI进行交互式API测试</em></p>
            </div>

            <h2>🚀 快速开始</h2>
            
            <div class="feature">
                <strong>1. 访问Swagger文档:</strong><br>
                <a href="/docs" target="_blank" style="font-size: 16px; font-weight: bold;">http://localhost:8000/docs</a><br>
                <em>在Swagger UI中可以直接测试所有API接口</em>
            </div>
            
            <div class="feature">
                <strong>2. 基础预测示例 (GET):</strong><br>
                <code>http://localhost:8000/predict?ship_type=Bulk Carrier&speed=12.0&dwt=75000</code>
            </div>
            
            <div class="feature">
                <strong>3. 增强预测示例 (POST):</strong><br>
                <pre style="background: #f4f4f4; padding: 10px; border-radius: 3px;">POST /predict
Content-Type: application/json

{
    "ship_type": "Bulk Carrier",
    "speed": 12.0,
    "dwt": 75000,
    "ship_age": 8,
    "load_condition": "Laden"
}</pre>
            </div>

            <h2>🏷️ 支持的船舶类型</h2>
            <ul>
                <li>Bulk Carrier (散货船)</li>
                <li>Container Ship (集装箱船)</li>
                <li>Crude Oil Tanker (原油船)</li>
                <li>Chemical Tanker (化学品船)</li>
                <li>General Cargo (杂货船)</li>
                <li>Open Hatch Cargo (开舱杂货船)</li>
                <li>Other (其他类型)</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 预测接口 - GET方式 (基础预测)
@app.get("/predict", response_model=PredictionResponse, summary="基础预测", description="使用查询参数进行基础油耗预测")
async def predict_get(
    ship_type: str = Query(..., description="船舶类型", example="Bulk Carrier"),
    speed: float = Query(..., ge=0, le=30, description="航行速度 (节)", example=12.0),
    dwt: Optional[float] = Query(None, ge=1000, description="载重吨", example=75000),
    ship_age: Optional[float] = Query(None, ge=0, le=50, description="船龄 (年)", example=8),
    load_condition: Optional[str] = Query("Laden", description="载重状态 (Laden/Ballast)", example="Laden")
):
    """基础预测接口 - GET方式"""
    if predictor_api is None:
        raise HTTPException(status_code=503, detail="预测服务未初始化")
    
    try:
        result = predictor_api.predict_enhanced(
            ship_type=ship_type,
            speed=speed,
            dwt=dwt,
            ship_age=ship_age,
            load_condition=load_condition
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return PredictionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")

# 预测接口 - POST方式 (增强预测)
@app.post("/predict", response_model=PredictionResponse, summary="增强预测", description="使用JSON请求体进行多维度增强预测")
async def predict_post(request: PredictionRequest):
    """增强预测接口 - POST方式"""
    if predictor_api is None:
        raise HTTPException(status_code=503, detail="预测服务未初始化")
    
    try:
        # 将请求模型转换为字典
        request_dict = request.dict(exclude_none=True)
        
        result = predictor_api.predict_enhanced(**request_dict)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return PredictionResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")

# 批量预测接口
@app.post("/predict/batch", summary="批量预测", description="批量处理多个预测请求")
async def predict_batch(request: BatchPredictionRequest):
    """批量预测接口"""
    if predictor_api is None:
        raise HTTPException(status_code=503, detail="预测服务未初始化")
    
    try:
        # 转换为预测请求列表
        batch_requests = []
        for pred_req in request.predictions:
            batch_requests.append(pred_req.dict(exclude_none=True))
        
        # 手动实现批量预测
        results = []
        for i, req in enumerate(batch_requests):
            try:
                result = predictor_api.predict_enhanced(**req)
                result['index'] = i
                results.append(result)
            except Exception as e:
                results.append({
                    'index': i,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return {
            "total_requests": len(batch_requests),
            "successful_predictions": len([r for r in results if 'predicted_consumption' in r]),
            "failed_predictions": len([r for r in results if 'error' in r]),
            "results": results,
            "processing_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量预测失败: {str(e)}")

# 载重状态对比分析
@app.post("/analyze/load-comparison", summary="载重状态对比", description="对比满载和压载状态下的油耗差异")
async def load_comparison(request: LoadComparisonRequest):
    """载重状态对比分析"""
    if predictor_api is None:
        raise HTTPException(status_code=503, detail="预测服务未初始化")
    
    try:
        ship_profile = request.dict(exclude_none=True)
        result = predictor_api.compare_load_conditions(ship_profile)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"载重状态对比失败: {str(e)}")

# 船龄影响分析
@app.post("/analyze/ship-age", summary="船龄影响分析", description="分析不同船龄对油耗的影响")
async def ship_age_analysis(
    ship_type: str = Query(..., description="船舶类型"),
    speed: float = Query(..., ge=0, le=30, description="航行速度 (节)"),
    dwt: Optional[float] = Query(None, ge=1000, description="载重吨"),
    age_min: float = Query(0, ge=0, le=30, description="最小船龄"),
    age_max: float = Query(25, ge=5, le=50, description="最大船龄")
):
    """船龄影响分析"""
    if predictor_api is None:
        raise HTTPException(status_code=503, detail="预测服务未初始化")
    
    try:
        ship_profile = {
            'ship_type': ship_type,
            'speed': speed,
            'dwt': dwt
        }
        
        result = predictor_api.analyze_ship_age_impact(
            ship_profile, 
            age_range=(age_min, age_max)
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"船龄分析失败: {str(e)}")

# 系统状态接口
@app.get("/status", summary="系统状态", description="获取API系统状态和配置信息")
async def get_status():
    """获取系统状态"""
    if predictor_api is None:
        return {
            "status": "error",
            "message": "预测服务未初始化",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        status = predictor_api.get_api_status_v3()
        status.update({
            "server_status": "running",
            "server_time": datetime.now().isoformat()
        })
        return status
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"状态查询失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# 支持的船舶类型列表
@app.get("/ship-types", summary="船舶类型列表", description="获取系统支持的船舶类型列表")
async def get_ship_types():
    """获取支持的船舶类型"""
    ship_types = [
        {
            "type": "Bulk Carrier",
            "chinese": "散货船",
            "description": "运输散装货物的船舶"
        },
        {
            "type": "Container Ship",
            "chinese": "集装箱船",
            "description": "运输集装箱的专用船舶"
        },
        {
            "type": "Crude Oil Tanker",
            "chinese": "原油船",
            "description": "运输原油的油轮"
        },
        {
            "type": "Chemical Tanker",
            "chinese": "化学品船",
            "description": "运输化学品的专用船舶"
        },
        {
            "type": "General Cargo",
            "chinese": "杂货船",
            "description": "运输各类杂货的船舶"
        },
        {
            "type": "Open Hatch Cargo",
            "chinese": "开舱杂货船",
            "description": "具有可开启舱盖的杂货船"
        },
        {
            "type": "Other",
            "chinese": "其他类型",
            "description": "其他类型的船舶"
        }
    ]
    
    return {
        "total_types": len(ship_types),
        "ship_types": ship_types,
        "supported_features": [
            "ship_type", "speed", "dwt", "ship_age", "load_condition",
            "draft", "length", "latitude", "longitude", 
            "heavy_fuel_cp", "light_fuel_cp", "speed_cp"
        ]
    }


# 错误处理
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "接口不存在",
        "message": "请检查API路径是否正确",
        "available_endpoints": [
            "/", "/predict", "/predict/batch", "/analyze/load-comparison",
            "/analyze/ship-age", "/status", "/ship-types", "/health", "/docs"
        ]
    }

if __name__ == "__main__":
    print("🚀 启动船舶油耗预测FastAPI服务器...")
    print("🌐 服务地址: http://localhost:8080")
    print("📖 Swagger文档: http://localhost:8080/docs")
    print("📋 ReDoc文档: http://localhost:8080/redoc")
    print("🏠 欢迎页面: http://localhost:8080")
    print("❤️ 健康检查: http://localhost:8080/health")
    print("")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
