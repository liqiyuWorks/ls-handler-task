#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
名片智能体配置文件
在这里可以自定义名片信息和智能体链接
"""

# 智能体链接（如需更换，可替换为你在平台上的专属对话链接）
AGENT_URL = "https://spectra.duplik.cn/client/chat/SP739496039699299?code=dAdpagIULXzYSsS7"

# 名片信息配置（根据需要修改为你的真实信息）
CARD_INFO = {
    "name": "赵开元",
    "title": "资深大宗商品航运、贸易专家",
    "company": "AquaBridge Shipping Pte. Ltd.",
    # 可按需填入你的常用邮箱
    "email": "kaiyuan.zhao@aquabridgeshipping.com",
    # 支持直接填入多部电话
    "phone": "+86 136 0106 5560 / +65 8731 2888",
    "website": "www.aquabridgeshipping.com",
    "address": "上海市浦东新区银城中路68号\n时代金融中心26层",
    "tags": [
        "大宗商品航运",
        "干散货贸易",
        "项目融资",
        "风险管理",
        "衍生品对冲"
    ],
    # 个人简介（可根据需要进一步润色）
    "bio": (
        "毕业于大连海事大学和长江商学院，长期深耕大宗商品航运与贸易领域。"
        "曾主导和参与价值超过10亿美元的散货船新造船项目及项目融资，"
        "为国内外头部粮食贸易商和金融机构提供长期运筹与风险管理服务。"
        "曾在波罗的海交易所北美唯一报价会员 JFD 负责亚洲业务，"
        "对全球航运及衍生品市场具有丰富的实战经验与深刻洞察。"
    ),
}

# 服务器配置
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "debug": True
}

