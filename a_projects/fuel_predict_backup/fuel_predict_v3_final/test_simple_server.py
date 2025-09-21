#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试服务器
Simple Test Server
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(
    title="船舶油耗预测API测试版",
    description="简化测试版本",
    version="3.0.0-test"
)

@app.get("/", response_class=HTMLResponse)
async def root():
    html = """
    <html>
    <head><title>船舶油耗预测API</title></head>
    <body>
        <h1>🚢 船舶油耗预测API V3.0</h1>
        <h2>📖 API文档</h2>
        <p><a href="/docs">Swagger UI: http://localhost:8000/docs</a></p>
        <p><a href="/redoc">ReDoc: http://localhost:8000/redoc</a></p>
        
        <h2>🧪 测试接口</h2>
        <p><a href="/test">测试接口: /test</a></p>
        <p><a href="/health">健康检查: /health</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "test"}

@app.get("/test")
async def test():
    return {"message": "Test successful", "swagger_url": "http://localhost:8000/docs"}

@app.get("/predict")
async def predict(ship_type: str = "Bulk Carrier", speed: float = 12.0):
    return {
        "predicted_consumption": 25.0,
        "ship_type": ship_type,
        "speed": speed,
        "message": "This is a test response",
        "swagger_docs": "http://localhost:8000/docs"
    }

if __name__ == "__main__":
    print("🚀 启动简化测试服务器...")
    print("🌐 服务地址: http://localhost:8000")
    print("📖 Swagger文档: http://localhost:8000/docs")
    print("📋 ReDoc文档: http://localhost:8000/redoc")
    print("🧪 测试接口: http://localhost:8000/test")
    print("❤️ 健康检查: http://localhost:8000/health")
    print("")
    
    uvicorn.run(
        "test_simple_server:app",
        host="0.0.0.0", 
        port=8000,
        reload=False
    )
