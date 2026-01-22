# -*- coding: utf-8 -*-
"""FastAPI 应用入口"""

import logging

from fastapi import FastAPI

from app.config import APP_DESC, APP_TITLE, APP_VERSION
from app.api.routes import parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESC,
    version=APP_VERSION,
)

app.include_router(parse.router, prefix="/api", tags=["parse"])
