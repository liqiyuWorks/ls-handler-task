#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
名片智能体配置文件
在这里可以自定义名片信息和智能体链接
"""

# 智能体链接（如需更换，可替换为你在平台上的专属对话链接）
AGENT_URL = "https://spectra.duplik.cn/client/chat/SP739496039703398?code=ZL642RWYgFtWvKBo"

# 名片信息配置（根据需要修改为你的真实信息）
CARD_INFO = {
    # 中文姓名为主，附带英文名便于国际合作场景
    "name": "赵开元 Terry Zhao",
    # 与名片保持一致，同时保留其在行业中的专业定位
    "title": "执行董事 · 资深大宗商品航运与贸易专家",
    # 使用名片上的公司全称
    "company": "Aquabridge Trading & Shipping Pte. Ltd.",
    # 根据名片补充的常用邮箱
    "email": "service@aquabridge.ai / terry@aquabridge.ai",
    # 按名片格式区分境外与境内联系方式及使用渠道
    "phone": "+65 8731 2888（Whatsapp） / +86 136 0106 5560（Wechat）",
    # 使用更通用的官网域名
    "website": "www.aquabridge.ai",
    # 与名片保持一致的中文办公地址，分行展示
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
        "毕业于大连海事大学和长江商学院，现任 Aquabridge Trading & Shipping Pte. Ltd. 执行董事，"
        "长期深耕大宗商品航运与贸易领域。"
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

