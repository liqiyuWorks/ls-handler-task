# -*- coding: utf-8 -*-
# Auto-reload test comment
"""FastAPI 应用入口"""

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.api.routes import parse, coze, auth, image
from app.services.database import db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESC,
    version=settings.APP_VERSION,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 这里的 "*" 仅建议在开发环境使用
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕捉所有未处理的异常并返回标准 JSON"""
    logger.exception("Unhandled exception occurred: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal Server Error",
            "detail": str(exc) if not settings.PLAYWRIGHT_HEADLESS else "Check server logs",
        },
    )


# 性能监控与请求日志中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    """计算请求耗时并在 Header 中返回，同时记录请求日志"""
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"

    logger.info(
        "Method: %s Path: %s Status: %s Duration: %.4fs",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response


# 路由包含
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(parse.router, prefix="/api", tags=["plugin"])
app.include_router(coze.router, prefix="/api/coze", tags=["coze"])
app.include_router(image.router, prefix="/api/image", tags=["image"])

# 挂载静态文件目录
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_db_client():
    await db.connect()


@app.on_event("shutdown")
async def shutdown_db_client():
    await db.disconnect()


@app.get("/health", tags=["system"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": settings.APP_VERSION}
