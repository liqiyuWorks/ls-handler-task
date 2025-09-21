#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import pymongo
from pkg.public.decorator import decorate
import json
from pkg.public.models import BaseModel
import logging
import os
import absl.logging
import numpy as np
import joblib
import pandas as pd
import tensorflow as tf
from tensorflow import keras
import warnings
from datetime import datetime
import traceback

# 在导入TensorFlow之前设置环境变量，避免GPU相关警告
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 禁用所有TensorFlow日志
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # 禁用OneDNN优化
os.environ['TF_MAC_ALLOCATOR'] = '1'  # 启用Mac特定的内存分配器
os.environ['TF_USE_CUDNN'] = '0'  # 禁用CUDA相关设置
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # 完全禁用CUDA设备
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'  # 禁用GPU内存增长
os.environ['TF_GPU_ALLOCATOR'] = 'cpu'  # 强制使用CPU分配器
os.environ['TF_TENSORRT_DISABLED'] = '1'  # 禁用TensorRT
os.environ['TF_CPU_ENABLE_AVX2'] = '1'  # 启用AVX2指令集
os.environ['TF_CPU_ENABLE_FMA'] = '1'  # 启用FMA指令集
os.environ['TF_ENABLE_MLIR_OPTIMIZATIONS'] = '0'  # 禁用MLIR优化
os.environ['TF_ENABLE_GPU_DEVICE_MEMORY_POOL'] = 'false'  # 禁用GPU内存池

warnings.filterwarnings('ignore')  # 关闭所有Python警告


def request_mmsi_detail(mmsi):
    url = "https://api.navgreen.cn/api/performance/vessel/speed"

    querystring = {"mmsi": mmsi, "version": "v1"}

    payload = ""
    headers = {
        "accept": "application/json",
        "token": "NAVGREEN_ADMIN_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjE1MDAxNTMsInVzZXJuYW1lIjoiaml1ZmFuZyIsImFjY2Vzc19rZXkiOiJMUzhBOUVGMTk2NDFGQkI1Q0Q4QUI3RUZFMjVGMUE3NSIsInNlY3JldF9rZXkiOiJMUzQzQkMzRUIzNkMyMzNDRDI0QTYwN0EzRkVDQUIxOCJ9.8zYU58Mxfiu-GDpOEGva1iGzxA0Dyexw1FoGfrdIrtc",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Host": "api.navgreen.cn"
    }

    response = requests.request(
        "GET", url, headers=headers, params=querystring)

    return response.json().get("data", [])


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return round(float(obj), 2)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# Mac specific TensorFlow configurations
# os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"   # 屏蔽 INFO/WARNING 级别日志
# os.environ['TF_MAC_ALLOCATOR'] = '1'  # 启用 Mac 特定的内存分配器
# os.environ['TF_USE_CUDNN'] = '0'  # 禁用 CUDA 相关设置


def get_check_svc_token(cache_rds):
    """检查和获取过期的海科 token """
    token = cache_rds.hget("svc", "access_token")
    return token


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


def pre_settings():
    # 设置TensorFlow日志级别
    tf.get_logger().setLevel('ERROR')
    tf.autograph.set_verbosity(0)
    
    # 设置日志级别
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger('absl').setLevel(logging.ERROR)
    absl.logging.set_verbosity(absl.logging.ERROR)
    
    # 关闭pandas警告
    pd.options.mode.chained_assignment = None
    
    # 完全禁用GPU，强制使用CPU
    try:
        # 隐藏所有GPU设备
        tf.config.set_visible_devices([], 'GPU')
        
        # 设置CPU线程配置
        tf.config.threading.set_inter_op_parallelism_threads(1)
        tf.config.threading.set_intra_op_parallelism_threads(1)
        
        # 禁用GPU内存增长
        for gpu in tf.config.experimental.list_physical_devices('GPU'):
            tf.config.experimental.set_memory_growth(gpu, False)
        
        # 设置CPU优化
        tf.config.optimizer.set_jit(False)  # 禁用JIT编译
        tf.config.optimizer.set_experimental_options({
            "layout_optimizer": False,
            "constant_folding": False,
            "shape_optimization": False,
            "remapping": False,
            "arithmetic_optimization": False,
            "dependency_optimization": False,
            "loop_optimization": False,
            "function_optimization": False,
            "debug_stripper": False,
        })
            
        print("TensorFlow configured to use CPU only with optimized settings")
    except Exception as e:
        print(f"TensorFlow configuration warning: {e}")
        pass


# 立即调用pre_settings来应用所有设置
pre_settings()

'''
@function predict_heavy_oil 预测重油消耗

@return predict_value -> number 预测值

@param load_status -> {-1, 1} 载重状态，-1代表Ballast, 1代表Laden
@param avg_speed -> number(>0) 实际平均速度(kts), 用于预测的话可以考虑租约速度或者失速模型, 但是要考虑与实际速度差异造成的误差
@param sailing_time -> number(>0) 航行时间(hrs)
@param load_weight -> number(>0) 船舶载重(t)
@param ship_draft -> number(>0) 船舶吃水(m)
@param length -> number(>0) 船舶长度
@param width -> number(>0) 船舶宽度
@param height -> number(>0) 船舶宽度
@param ship_year -> number(>=0) 船龄, 若没有则输入0
'''


def get_current_dirs(path):
    dirs = []
    for dir in os.listdir(path):
        dir = os.path.join(path, dir)
        # 判断当前目录是否为文件夹
        if os.path.isdir(dir) and "__pycache__" not in dir:
            dirs.append(dir)
    return dirs


def predict_heavy_oil(load_status, avg_speed, sailing_time, load_weight, ship_draft, length, width, height, ship_year):
    base_path = os.path.dirname(os.path.abspath(__file__))
    dirs_list = get_current_dirs(base_path)
    pre_dir = dirs_list[0]
    data_scaler_X = joblib.load(f'{pre_dir}/minmax_scaler.pkl')  # scaler模型路径
    X_test = np.array([[load_status, avg_speed, sailing_time,
                      load_weight, ship_draft, length, width, height, ship_year]])
    X_test_df = pd.DataFrame(X_test, columns=[
                             '载重状态', '平均速度(kts)', '航行时间(hrs)', '船舶载重(t)', '船舶吃水(m)', 'length', 'width', 'height', '船龄'])
    X_test_df = data_scaler_X.transform(X_test_df)

    y_pred_list = []

    for i in range(5):
        try:
            model_path = f'{pre_dir}/fuel_model_' + str(i) + '.h5'  # 预测模型路径
            loaded_model = keras.models.load_model(model_path)
            if loaded_model is None:
                raise ValueError(f"Failed to load model from {model_path}")
            y_pred = loaded_model.predict(X_test_df, verbose=0)
            if y_pred is None:
                raise ValueError(
                    f"Model prediction returned None for model {i}")
            y_pred_list.append(y_pred[:, 0])
        except Exception as e:
            print(f"Error with model {i}: {str(e)}")
            continue

    if not y_pred_list:
        raise ValueError("No valid predictions were made")

    y_avg_pred = []

    y_pred_i_list = []
    for j in range(len(y_pred_list)):
        y_pred_i_list.append(y_pred_list[j][0])
    y_pred_i_list.pop(y_pred_i_list.index(max(y_pred_i_list)))
    y_pred_i_list.pop(y_pred_i_list.index(min(y_pred_i_list)))
    y_avg_pred.append(sum(y_pred_i_list)/3)

    return y_avg_pred[0]



class CalculateVesselPerformanceCK(BaseModel):
    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }
        super(CalculateVesselPerformanceCK, self).__init__(config)
        # 检查 mgo_db 是否初始化成功
        if not hasattr(self, 'mgo_db') or self.mgo_db is None:
            raise RuntimeError(
                'MongoDB 未正确初始化，请检查环境变量 MONGO_DB、MONGO_HOST、MONGO_PORT 或 MONGO_REPLICA_SET_URL 是否设置。')

    @decorate.exception_capture_close_datebase
    def run(self, task, cache_rds):
        try:
            process_data = task.get("process_data")

            if process_data:
                print(process_data)
                year_month = datetime.now().strftime("%Y%m")
                version = "v2"
                sailing_time = 24
                mmsi = process_data.get("mmsi")
                print(list(process_data.keys()))
                if list(process_data.keys()) == ['mmsi']:
                    print("字典仅包含 mmsi 键")
                    try:
                        res = request_mmsi_detail(mmsi)
                        print(res)
                    except Exception as e:
                        print("error:", e)
                else:
                    print("字典包含其他键")
                    avg_good_weather_speed = process_data.get(
                        "avg_good_weather_speed")
                    avg_ballast_speed = process_data.get("avg_ballast_speed")
                    avg_laden_speed = process_data.get("avg_laden_speed")

                    load_weight = process_data.get("load_weight")
                    ship_draft = process_data.get("ship_draft")
                    ballast_draft = process_data.get("ballast_draft")

                    length = process_data.get("length")
                    width = process_data.get("width")
                    height = process_data.get("height")
                    ship_year = process_data.get("ship_year")

                    avg_ballast_fuel = None
                    avg_laden_fuel = None
                    avg_fuel = None
                    if avg_good_weather_speed:
                        avg_laden_fuel = round(predict_heavy_oil(
                            1, avg_good_weather_speed, sailing_time, load_weight, ship_draft, length, width, height, ship_year), 2)
                    print(avg_good_weather_speed, sailing_time, load_weight,
                          ship_draft, length, width, height, ship_year)
                    avg_ballast_fuel = round(predict_heavy_oil(-1, avg_good_weather_speed, sailing_time,
                                                               load_weight, ship_draft, length, width, height, ship_year), 2)

                    if avg_laden_fuel and avg_ballast_fuel:
                        avg_fuel = round(
                            (avg_laden_fuel+avg_ballast_fuel)/2, 2)

                    process_data["avg_fuel"] = avg_fuel
                    process_data["avg_laden_fuel"] = avg_laden_fuel
                    process_data["avg_ballast_fuel"] = avg_ballast_fuel
                    print("满载油耗", avg_laden_fuel)
                    print("空载油耗", avg_ballast_fuel)
                    print("平均油耗", avg_fuel)

                    # 更新cache_rds的数据 -- 2025 年 6 月 4 日 13:29:07 废弃
                    # cache_rds.hset(
                    #     f"vessels_performance_{version}|{year_month}",  f"{mmsi}", json.dumps(process_data, cls=NumpyEncoder))
                    # print(
                    #     "已更新", f"vessels_performance_{version}|{year_month} - {mmsi}", "成功")

                    # 更新mgo的船舶性能数据
                    if not hasattr(self, 'mgo_db') or self.mgo_db is None:
                        raise RuntimeError(
                            'MongoDB 未正确初始化，请检查环境变量 MONGO_DB、MONGO_HOST、MONGO_PORT 或 MONGO_REPLICA_SET_URL 是否设置。')
                    self.mgo_db["vessels_performance_details"].update_one(
                        {"mmsi": int(mmsi)},
                        {"$set": {"current_performance_fuel": convert_numpy(process_data)}},
                        upsert=True
                    )

        except Exception as e:
            traceback.print_exc()
            print("error:", e)


# 新增递归转换 numpy 类型的工具函数
def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return round(float(obj), 2)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
