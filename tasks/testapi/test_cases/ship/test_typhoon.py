#!/usr/bin/python
# -*- coding: utf-8 -*-
import pytest
from common.request_util import request_handler
from common.yaml_util import read_yaml_test_cases

class TestShip:
    @pytest.mark.parametrize('casinfo', read_yaml_test_cases('tasks/testapi/test_cases/ship/cfg_typhoon_newest.yaml'))
    def test_typhoon_forecast_newest(self, casinfo):
        method = casinfo['request']['method']
        host = casinfo['request'].get("host")
        path = casinfo['request'].get("path")
        url = host + path
        response = request_handler(method, url)
        assert response['code'] == casinfo["assert_expression"]
        # assert response['code'] == 1
        
    @pytest.mark.parametrize('casinfo', read_yaml_test_cases('tasks/testapi/test_cases/ship/cfg_typhoon_deduce.yaml'))
    def test_typhoon_current_deduce(self, casinfo):
        method = casinfo['request']['method']
        host = casinfo['request'].get("host")
        path = casinfo['request'].get("path")
        url = host + path
        response = request_handler(method, url)
        assert response['code'] == casinfo["assert_expression"]