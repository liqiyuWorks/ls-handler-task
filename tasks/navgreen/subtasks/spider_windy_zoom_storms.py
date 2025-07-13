#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import requests
import datetime
from pkg.public.models import BaseModel
import traceback
from pkg.public.logger import logger
import json


def get_newest_token(cache_redis):
    url = "https://account.windy.com/api/info"

    querystring = {"country": "sg"}

    headers = {
        "Origin": "capacitor://app-webview.windy.com",
        "Accept": "application/json binary/4413mobc40b token/d6df4064e2379e732d643d20afbf3b9b",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Dest": "empty",
        "Host": "account.windy.com",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Sec-Fetch-Mode": "cors",
        "windy-csrf": "zs/Am4/CnpyckIqRi9CWkZmQ2ZuTwpyej56clouQjdrMvtrNudrNuZ6Pj9KImp2JlpqI0YiWkZuG0ZyQktmekcKolpGbhtmclpvCm5yemcmbzs/SnJ7PyNLLyceZ0sfNy57SnZmczs7HzJnGzcrO2YyNwszGzIfHys3ZipfCzpaVjJOeypjOz86aycyazs7PyJ3NmcrZipPCmpHSqqzZnpabwpyQktGIlpGbhtGWkIzZmYnCi42KmtmMjMKLjYqa2ZuLws7IzMbMy8bHxs/KzMjZm43C2ZqLws8=",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cookie": "_account_ss=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ODgyMTA4OCwidXNlcm5hbWUiOiJsaXFpeXVXb3JrcyIsImVtYWlsIjoiamFja2xlZWxpc2hlbmdAZ21haWwuY29tIiwiaWF0IjoxNzQxOTM4MDMxfQ.GE4DR_a4ebZUTdwZ5lJAPYpY9WWJVTuXrm6hjMPNNZA;_account_sid=s%3AMdg9k5DsOIM5R0hZwA-pfw9aBxVsHl7b.HKmgplkKt75eZoHPJdr%2BExqj%2FOMF1%2BGtGcdEoLTxE%2F8"
    }

    response = requests.get(
        url=url,
        headers=headers,
        data=querystring)

    token = response.json().get("token")

    cache_redis.hset("windy", "jackleelisheng@gmail", token)
    cache_redis.expire("windy", 3600*24)  # 3600*24 -> 1 day
    return token


def get_check_token_expired(cache_redis):
    token2 = cache_redis.hget("windy", "jackleelisheng@gmail")
    if not token2:
        # 获取新的token
        token2 = get_newest_token(cache_redis)
        print(f"get new token from windy success!,token2={token2}")
    else:
        print(f"get token from cache success!,token2={token2}")
        token2 = token2
    return token2


def request_svc_detail(token, mmsi_list):
    url = "https://svc.data.myvessel.cn/sdc/v1/vessels/details"

    payload = {"mmsiList": mmsi_list}
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        url=url,
        headers=headers,
        json=payload)

    return response.json().get("data", [])


class SpiderWindyZoomStorms(BaseModel):
    def __init__(self):
        config = {
            "cache_rds": True
        }

        super(SpiderWindyZoomStorms, self).__init__(config)

    def get_windy_storms(self, windy_token):
        url = f"https://node.windy.com/tc/v2/storms?pr=0&sc=23&token2={windy_token}"

        response = requests.get(url=url)
        storms = response.json().get("storms", [])

        return storms

    def get_windy_storm_track(self, windy_token, storm_name):
        url = f"https://node.windy.com/tc/v2/storms/{storm_name}?pr=0&sc=23&token2={windy_token}"

        response = requests.get(url=url)

        return response.json()

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            windy_token = get_check_token_expired(self.cache_rds)
            data = []
            storms = self.get_windy_storms(windy_token)
            for storm in storms:
                id = storm.get("id")
                track = self.get_windy_storm_track(windy_token, id)
                data.append(track)

            windy_current_storms = {
                "data": data,
                "fresh_time": dataTime
            }
            logger.info(f"fresh ok, windy_current_storms={windy_current_storms}")

            # 设置缓存
            self.cache_rds.set("windy_current_storms",
                               json.dumps(windy_current_storms))

        except Exception as e:
            traceback.print_exc()
