# -*- coding: utf-8 -*-
"""FastAPI 应用入口"""

import logging

from fastapi import FastAPI

from app.config import APP_DESC, APP_TITLE, APP_VERSION
from app.api.routes import parse, coze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESC,
    version=APP_VERSION,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse.router, prefix="/api", tags=["parse"])
app.include_router(coze.router, prefix="/api/coze", tags=["coze"])
