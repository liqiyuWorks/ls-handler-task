#!/usr/bin/python
# -*- coding: utf-8 -*-
import pytest
from common.request_util import request_handler
from common.yaml_util import read_yaml_test_cases
import os
import datetime

DEFAULT_HOST = os.getenv("DEFAULT_HOST", "http://0.0.0.0:7060")


class TestMeteo:
    @pytest.mark.parametrize('casinfo', read_yaml_test_cases('tasks/testapi/test_cases/meteo/cfg_meteo_json_pressure.yaml'))
    def test_json_pressure(self, casinfo):
        method = casinfo['request']['method']
        host = casinfo['request'].get("host", DEFAULT_HOST)
        path = casinfo['request'].get("path")
        url = host + path
        timestamp = int(datetime.datetime.now().timestamp())*1000
        response = request_handler(method, url, {"timestamp":timestamp})
        assert response.status_code == 200
        
        
    @pytest.mark.parametrize('casinfo', read_yaml_test_cases('tasks/testapi/test_cases/meteo/cfg_meteo_json_seawaveheight.yaml'))
    def test_json_seawaveheight(self, casinfo):
        method = casinfo['request']['method']
        host = casinfo['request'].get("host", DEFAULT_HOST)
        path = casinfo['request'].get("path")
        url = host + path
        timestamp = int(datetime.datetime.now().timestamp())*1000
        response = request_handler(method, url, {"timestamp":timestamp})
        assert response.status_code == 200