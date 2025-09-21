#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
from lxml import html
import datetime
import json
import pymongo
import requests
from pkg.public.models import BaseModel


import json

import requests


def tranlate(source, direction="auto2zh"):
    url = "http://api.interpreter.caiyunai.com/v1/translator"

    # WARNING, this token is a test token for new developers,
    # and it should be replaced by your token
    token = "dbvfl2ap5a0vxiks0dhi"

    payload = {
        "source": source,
        "trans_type": direction,
        "request_id": "demo",
        "detect": True,
    }

    headers = {
        "content-type": "application/json",
        "x-authorization": "token " + token,
    }

    response = requests.request(
        "POST", url, data=json.dumps(payload), headers=headers)

    return json.loads(response.text)["target"]


class SpiderMarinelink(BaseModel):
    Marinelink_URL = "https://www.marinelink.com/"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'marinelink_papers',
            'uniq_idx': [
                ('aid', pymongo.ASCENDING),
                # ('date', pymongo.ASCENDING),
            ]
        }
        super(SpiderMarinelink, self).__init__(config)

    def query_article(self, url):
        # print(f'链接地址：{url}')
        res = requests.get(url=url)
        # 使用lxml库解析网页内容
        tree = html.fromstring(res.content)
        texts = tree.xpath('//*[@class="fr-view"]//p//text()')
        eng_text_list = []
        for text in texts:
            # print(text)
            eng_text_list.append(text)
        zh_text_list = tranlate(eng_text_list, "auto2zh")
        return eng_text_list, zh_text_list

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d")
        res = requests.get(url=self.Marinelink_URL)
        # 使用lxml库解析网页内容
        tree = html.fromstring(res.content)
        # tree = etree.HTML(res.content)
        # 找出所有的<a>标签
        links = tree.xpath('//a')

        # 遍历所有的链接并打印出对应的内容
        item = {}
        for link in links:
            href = link.get('href')  # 获取链接地址
            if "/news/" not in href or "maritime" in href:
                continue
            link_text = link.text_content()  # 获取链接文本
            # print(f'链接文本：{link_text}')
            aid = str(href).split("/")[-1]
            url = self.Marinelink_URL+href
            eng_text_list, zh_text_list = self.query_article(url=url)
            item = {
                "aid": aid,
                "eng_link_text": link_text,
                "zh_link_text": tranlate(link_text, "auto2zh"),
                "date": dataTime,
                "eng_text_list": eng_text_list,
                "zh_text_list": zh_text_list,
            }

            self.mgo.set(None, item)
            print(aid, " - ", dataTime, "success")
            # break
