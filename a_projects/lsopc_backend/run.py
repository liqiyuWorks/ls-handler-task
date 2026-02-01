#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动 FastAPI 服务"""

import os
import uvicorn

from app.config import HOST, PORT

if __name__ == "__main__":
    reload = os.getenv("RELOAD", "true").lower() == "true"
    print(f"Starting server with reload={reload}")
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=reload,
    )
