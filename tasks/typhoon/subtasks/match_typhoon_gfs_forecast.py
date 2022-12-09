#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate


class MatchTyphoonGfsForecast(BaseModel):
    def __init__(self, config=None):
        config = {'handle_db': 'mgo'}
        super().__init__(config)
    
    @decorate.exception_capture_close_datebase
    def run(self):
        print(self.mgo_db)
        print(">>>>>>>> processing ...")