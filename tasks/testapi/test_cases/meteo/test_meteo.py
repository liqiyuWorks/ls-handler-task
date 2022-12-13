#!/usr/bin/python
# -*- coding: utf-8 -*-
import pytest
from common.request_util import request_handler
from common.yaml_util import read_yaml_test_cases
import os

DEFAULT_HOST = os.getenv("DEFAULT_HOST", "http://0.0.0.0:7060")


class TestMeteo:
    @pytest.mark.parametrize('casinfo', read_yaml_test_cases('tasks/testapi/test_cases/meteo/cfg_meteo_wwc.yaml'))
    def test_wwc(self, casinfo):
        method = casinfo['request']['method']
        host = casinfo['request'].get("host", DEFAULT_HOST)
        path = casinfo['request'].get("path")
        url = host + path
        data = casinfo['request']['data']
        response = request_handler(method, url, data)
        assert response['code'] == casinfo["assert_expression"]
        # logger.info(response)