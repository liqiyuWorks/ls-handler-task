#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pkg.db.mongo import get_mgo, MgoStore
import pymongo

class BaseModel:
    def __init__(self):
        pass

    def close(self):
        pass

    def history(self):
        pass
         
    def run(self):
        pass
