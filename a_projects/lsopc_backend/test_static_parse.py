#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口：已迁移至 app 包，请优先使用 run.py 启动。"""

if __name__ == "__main__":
    import uvicorn

    from app.config import HOST, PORT

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
