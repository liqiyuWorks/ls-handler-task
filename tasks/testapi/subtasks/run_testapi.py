#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import datetime
from pkg.public.models import BaseModel
import pytest
import logging

class RunTestApi(BaseModel):
    def __init__(self, testapi_path):
        self.testapi_path = testapi_path
    
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        pytest.main(["-vs", self.testapi_path])
        print(f" => run {self.testapi_path} success!")

