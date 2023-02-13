#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.consumer.subtasks.convert_nc2json_rds import ConvertGFSnc2jsonRds, ConvertMFWAMnc2jsonRds


def get_task_dic():
    task_dict = {
        "convert_gfs_nc2json_rds": (lambda: ConvertGFSnc2jsonRds(), '消费者=> 转换GFS的nc成json, 并上传到obs'),
        "convert_mfwam25_nc2json_rds": (lambda: ConvertMFWAMnc2jsonRds(), '消费者=> 转换mfwam的0.25精度的nc成json, 并上传到obs'),
    }
    return task_dict
