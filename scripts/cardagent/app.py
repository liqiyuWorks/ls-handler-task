#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
名片智能体 Web 服务
提供名片展示和智能体聊天功能
"""

from flask import Flask, render_template
import os

# 导入配置
try:
    from config import AGENT_URL, CARD_INFO, SERVER_CONFIG
except ImportError:
    # 如果配置文件不存在，使用默认配置
    AGENT_URL = "https://spectra.duplik.cn/client/chat/SP739496039699299?code=dAdpagIULXzYSsS7"
    CARD_INFO = {
        "name": "您的姓名",
        "title": "职位/头衔",
        "company": "公司名称",
        "email": "your.email@example.com",
        "phone": "+86 138 0000 0000",
        "website": "www.example.com",
        "address": "中国 · 城市",
        "tags": ["专业领域1", "专业领域2", "专业领域3"]
    }
    SERVER_CONFIG = {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": True
    }

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(current_dir, 'templates'),
    static_folder=os.path.join(current_dir, 'static')
)

@app.route('/')
def index():
    """名片智能体主页"""
    return render_template('index.html', 
                         agent_url=AGENT_URL,
                         card_info=CARD_INFO)

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs(os.path.join(current_dir, 'templates'), exist_ok=True)
    os.makedirs(os.path.join(current_dir, 'static'), exist_ok=True)
    
    print("🚀 名片智能体服务启动中...")
    print(f"📱 访问地址: http://localhost:{SERVER_CONFIG['port']}")
    print(f"🤖 智能体链接: {AGENT_URL}")
    
    app.run(
        debug=SERVER_CONFIG['debug'],
        host=SERVER_CONFIG['host'],
        port=SERVER_CONFIG['port']
    )

