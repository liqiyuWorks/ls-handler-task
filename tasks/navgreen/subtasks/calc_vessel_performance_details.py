#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymongo
from pkg.public.decorator import decorate
import json
from pkg.public.models import BaseModel
import logging
import os
from datetime import datetime


class CalcVesselPerformanceDetails(BaseModel):
    def __init__(self):
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'vessels_performance_details',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }

        super(CalcVesselPerformanceDetails, self).__init__(config)

    def run(self):
        try:
            print("calc_vessel_speed_details")

        except Exception as e:
            print("error:", e)
