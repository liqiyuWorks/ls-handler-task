#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import re
import datetime
import json
import pymongo
import requests
from pkg.public.models import BaseModel


class SpiderEtsPrices(BaseModel):
    # ETS_PRICE_URL = "https://flo.uri.sh/visualisation/12603037/embed?auto=1"
    ETS_PRICE_URL = "http://new-carbon-price-viewer-fdc966f57ddd.herokuapp.com/_dash-layout"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'ets_prices',
            'uniq_idx': [
                ('day', pymongo.ASCENDING),
            ]
        }
        super(SpiderEtsPrices, self).__init__(config)

    def run_old_ets(self):
        # dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        res = requests.get(url=self.ETS_PRICE_URL)
        if res.status_code == 200:
            # print(res.text)
            try:
                data_match = re.search(
                    r"_Flourish_data\s=\s(.*?)}]}", res.text).group(1)
            except Exception as e:
                print(e)
            data_match = str(data_match) + "}]}"
            # print(data_match)
            data_json = json.loads(data_match)
            for k, v in data_json.items():
                for j in v:
                    print(j)
                    day = j["label"]
                    # if day
                    item = {"day": day, "value": j["value"][0]}
                    self.mgo.set(None, item)

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = (datetime.datetime.now() -
                    datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        res = requests.get(url=self.ETS_PRICE_URL, timeout=60)
        if res.status_code == 200:
            data = res.json().get("props", {}).get("children", [])[1].get(
                "props", {}).get("children", [])[1].get("props", {}).get(
                    "children", [])[0].get("props", {}).get("figure").get("data", [])
            print(data)

            days = data[0].get("x")
            prices = data[0].get("y")
            for day, value in zip(days, prices):
                if day < dataTime:
                    continue
                item = {"day": day[:10], "value": str(round(value, 2))}
                self.mgo.set(None, item)
