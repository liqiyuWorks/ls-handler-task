#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI接口服务器 - 车辆报告二维码修改服务
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import os
import urllib.parse
from auto_date_modifier_advanced import AdvancedAutoDateModifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="车辆报告二维码修改API",
    description="自动修改车辆报告页面中的日期和二维码图片，支持浏览器预览修改结果",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "defaultModelExpandDepth": 3,
        "displayRequestDuration": True,
        "docExpansion": "list"
    }
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建screenshots目录
os.makedirs("screenshots", exist_ok=True)

# 挂载静态文件服务
app.mount("/screenshots", StaticFiles(directory="."), name="screenshots")

# 请求模型
class ModifyRequest(BaseModel):
    date: Optional[str] = Field(
        None, 
        description="新日期 (YYYY-MM-DD格式)，不提供则使用当前日期",
        example="2024-12-25"
    )
    vin: Optional[str] = Field(
        "LE4ZG8DB3ML639548", 
        description="车辆VIN码",
        example="LE4ZG8DB3ML639548"
    )
    qr_url: Optional[str] = Field(
        "https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg",
        description="二维码图片URL",
        example="https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg"
    )
    headless: bool = Field(
        True, 
        description="是否无头模式运行",
        example=True
    )

# 响应模型
class ModifyResponse(BaseModel):
    success: bool = Field(..., description="是否成功", example=True)
    message: str = Field(..., description="响应消息", example="修改成功")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    timestamp: str = Field(..., description="响应时间戳", example="2024-12-25T14:30:22.123456")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "车辆报告二维码修改API服务",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    健康检查
    
    检查API服务是否正常运行。
    
    返回服务状态和时间戳。
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/modify", response_model=ModifyResponse)
async def modify_report(request: ModifyRequest):
    """
    修改车辆报告
    
    自动修改车辆报告页面中的日期和二维码图片。
    
    - **date**: 新日期 (YYYY-MM-DD格式)，不提供则使用当前日期
    - **vin**: 车辆VIN码
    - **qr_url**: 二维码图片URL
    - **headless**: 是否无头模式运行
    
    返回修改结果，包含截图预览URL，可直接在浏览器中查看修改效果。
    """
    try:
        # 如果没有提供日期，使用当前日期
        if not request.date:
            request.date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"收到修改请求: VIN={request.vin}, 日期={request.date}")
        
        # 创建修改器实例
        modifier = AdvancedAutoDateModifier(
            vin=request.vin,
            new_date=request.date,
            qr_code_url=request.qr_url,
            headless=request.headless
        )
        
        # 执行修改
        success, screenshot_path = await modifier.run()
        
        if success:
            # 构建图片预览URL
            preview_url = f"http://localhost:8000/preview/{screenshot_path}" if screenshot_path else None
            
            response_data = {
                "vin": request.vin,
                "date": request.date,
                "qr_url": request.qr_url,
                "screenshot_path": screenshot_path,
                "preview_url": preview_url,
                "modification_time": datetime.now().isoformat()
            }
            
            return ModifyResponse(
                success=True,
                message="修改成功",
                data=response_data,
                timestamp=datetime.now().isoformat()
            )
        else:
            # 构建错误截图预览URL
            error_preview_url = f"http://localhost:8000/preview/{screenshot_path}" if screenshot_path else None
            
            response_data = {
                "vin": request.vin,
                "date": request.date,
                "qr_url": request.qr_url,
                "error_screenshot": screenshot_path,
                "error_preview_url": error_preview_url,
                "modification_time": datetime.now().isoformat()
            }
            
            return ModifyResponse(
                success=False,
                message="修改失败",
                data=response_data,
                timestamp=datetime.now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"修改过程中出错: {e}")
        raise HTTPException(status_code=500, detail=f"修改失败: {str(e)}")

@app.get("/info")
async def get_service_info():
    """
    获取服务信息
    
    返回API服务的详细信息，包括版本、描述、可用接口等。
    """
    return {
        "service_name": "车辆报告二维码修改API",
        "version": "1.0.0",
        "description": "自动修改车辆报告页面中的日期和二维码图片，支持浏览器预览修改结果",
        "endpoints": {
            "modify": "POST /modify - 修改车辆报告",
            "health": "GET /health - 健康检查",
            "info": "GET /info - 服务信息",
            "preview": "GET /preview/{filename} - 预览截图"
        },
        "default_parameters": {
            "vin": "LE4ZG8DB3ML639548",
            "qr_url": "https://teststargame.oss-cn-shanghai.aliyuncs.com/getQRCode-2.jpg",
            "headless": True
        }
    }

@app.get("/preview/{filename}")
async def preview_screenshot(filename: str):
    """
    预览截图文件
    
    在浏览器中直接预览修改后的截图文件。
    
    - **filename**: 截图文件名
    
    返回图片文件，支持浏览器直接显示。
    """
    file_path = filename
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="截图文件不存在")

@app.get("/screenshots")
async def list_screenshots():
    """
    列出所有截图文件
    
    获取所有可用的截图文件列表，包括文件名、URL、大小和修改时间。
    
    返回截图文件列表，可用于浏览和管理所有修改结果。
    """
    screenshots = []
    for file in os.listdir("."):
        if file.endswith((".png", ".jpg", ".jpeg")) and ("report" in file or "screenshot" in file):
            screenshots.append({
                "filename": file,
                "url": f"/preview/{file}",
                "size": os.path.getsize(file) if os.path.exists(file) else 0,
                "modified": datetime.fromtimestamp(os.path.getmtime(file)).isoformat() if os.path.exists(file) else None
            })
    
    return {
        "total": len(screenshots),
        "screenshots": sorted(screenshots, key=lambda x: x["modified"], reverse=True) if screenshots else []
    }

@app.get("/result", response_class=HTMLResponse)
async def show_result_page():
    """显示结果页面"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>车辆报告修改结果</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .result-card { background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .success { border-left: 5px solid #28a745; }
            .error { border-left: 5px solid #dc3545; }
            .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .info-item { background: white; padding: 15px; border-radius: 5px; }
            .screenshot { max-width: 100%; height: auto; border-radius: 5px; margin-top: 15px; }
            .btn { display: inline-block; padding: 10px 20px; margin: 5px; border-radius: 5px; text-decoration: none; color: white; background: #007bff; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚗 车辆报告修改结果</h1>
                <p>自动修改车辆报告页面中的日期和二维码图片</p>
            </div>
            <div id="result">
                <div class="result-card">
                    <h2>欢迎使用车辆报告修改API</h2>
                    <p>请使用API接口进行修改操作，或访问API文档了解更多信息。</p>
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="/docs" class="btn">📖 查看API文档</a>
                        <a href="/screenshots" class="btn">📸 查看所有截图</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True) 