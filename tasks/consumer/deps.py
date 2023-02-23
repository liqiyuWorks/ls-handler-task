
import numpy as np
import sys
import os
from netCDF4 import Dataset
import logging
from obs import ObsClient
from datetime import datetime, timedelta
import time


class ObsStore(object):
    def __init__(self, config):
        self.config = config
        # 华为云存储
        self.obs_client = ObsClient(
            access_key_id=config['obs_ak'],
            secret_access_key=config['obs_sk'],
            server=config['obs_server']
        )
        self.obs_bucket = config['obs_bucket']
        self.obs_domain = config['obs_domain']
        self.obs_root = config['obs_root']

    def set(self, data):
        file_name = data['file_name']
        obs_key = '{}/{}'.format(self.obs_root, data['obs_key'])
        obs_res = self.obs_client.putFile(self.obs_bucket, obs_key, file_name)
        if obs_res.status != 200:
            logging.error(
                'upload {} failed, res {}'.format(file_name, obs_res))
            return None
        # logging.info(obs_res.body.objectUrl)
        return '{}/{}'.format(self.obs_domain, obs_key)


def check_create_path(file):
    file_path = os.path.dirname(file)
    if not os.path.exists(file_path):
        os.makedirs(file_path, 0o775)


def list_dir(path, res):
    for i in os.listdir(path):
        temp_dir = os.path.join(path, i)
        if os.path.isdir(temp_dir):
            temp = {"dirname": temp_dir, 'child_dirs': [], 'files': []}
            res['child_dirs'].append(list_dir(temp_dir, temp))
        else:
            res['files'].append(i)
    return res


def get_default_value(nc_obj, value_name):
    attributes = nc_obj[value_name].ncattrs()
    if 'missing_value' in attributes:
        return nc_obj[value_name].getncattr('missing_value')
    else:
        return nc_obj[value_name].getncattr('_FillValue')


def format_time(india_time_str, india_format='%Y%m%d%H%M', hours=8):
    india_dt = datetime.strptime(india_time_str, india_format)
    local_dt = india_dt + timedelta(hours=hours)
    # local_format = "%Y-%m-%d %H:%M:%S"
    # time_str = local_dt.strftime(local_format)
    return local_dt


def read_gfs_press_nc(input_path):
    try:
        with Dataset(input_path) as nc_obj:
            file_list = input_path.split(".")
            date_str = file_list[0].split("/")[-2]
            delta_hour = int(file_list[-2].replace("f", ""))
            # print(f"> 文件时间: {date_str} => {delta_hour}")
            since_time = datetime.strptime(date_str, "%Y%m%d%H")
            latitude_li = (nc_obj.variables['lat_0'][:])
            longitude_li = (nc_obj.variables['lon_0'][:])
            values_array = []
            for value_name in ["PRMSL_P0_L101_GLL0"]:
                try:
                    value_li = np.array(nc_obj[value_name][:])
                except Exception as e:
                    logging.error(
                        f"=> Gfs not find {value_name}(pressure) in {input_path}")
                    return None
                missing_value = get_default_value(nc_obj, value_name)
                values_dict = {'value_name': value_name,
                               'value_li': value_li, 'missing_value': missing_value}
                values_array.append(values_dict)
    except Exception as e:
        logging.error(f"=> gfs 没有该文件：{input_path}")
        return None
    else:
        # 转换成时间数组
        dt = since_time + timedelta(hours=delta_hour)

        array = []
        for lat_index in range(0, len(latitude_li)):
            for lon_index in range(0, len(longitude_li)):
                for value_dict in values_array:
                    value_name = value_dict['value_name']
                    value = float(value_dict['value_li'][lat_index][lon_index])
                    missing_value = value_dict['missing_value']
                    # if value == missing_value:
                    #     continue
                    array.append(round(value, 2))

        print(">>> array 长度", len(array), len(latitude_li), len(longitude_li))
        data = {
            "dt": dt.strftime("%Y%m%d%H"),
            "data": {"array": array, "latLgh": len(latitude_li), "lonLgh": len(longitude_li)}
        }
        return data


def read_gfs_wind_nc(input_path):
    try:
        with Dataset(input_path) as nc_obj:
            file_list = input_path.split(".")
            date_str = file_list[0].split("/")[-2]
            delta_hour = int(file_list[-2].replace("f", ""))
            # print(f"> 文件时间: {date_str} => {delta_hour}")
            since_time = datetime.strptime(date_str, "%Y%m%d%H")
            latitude_li = (nc_obj.variables['lat_0'][:])
            longitude_li = (nc_obj.variables['lon_0'][:])
            values_array = []
            for value_name in ["UGRD_P0_L103_GLL0"]:
                try:
                    value_li = np.array(nc_obj[value_name][0])
                except Exception as e:
                    logging.error(
                        f"=> Gfs not find {value_name}(wind) in {input_path}")
                    return None
                missing_value = get_default_value(nc_obj, value_name)
                values_dict = {'value_name': value_name,
                               'value_li': value_li, 'missing_value': missing_value}
                values_array.append(values_dict)
    except Exception:
        logging.error(f"=> gfs 没有该文件：{input_path}")
        return None
    else:
        # 转换成时间数组
        dt = since_time + timedelta(hours=delta_hour)

        array = []
        for lat_index in range(0, len(latitude_li)):
            for lon_index in range(0, len(longitude_li)):
                for value_dict in values_array:
                    value_name = value_dict['value_name']
                    value = float(value_dict['value_li'][lat_index][lon_index])
                    missing_value = value_dict['missing_value']
                    # if value == missing_value:
                    #     continue
                    array.append(round(value, 2))

        print(">>> array 长度", len(array), len(latitude_li), len(longitude_li))
        data = {
            "dt": dt.strftime("%Y%m%d%H"),
            "data": {
                "header": {
                    "nx": 1440,
                    "ny": 721,
                    "lo1": -180,
                    "la1": 90,
                    "lo2": 179.75,
                    "la2": -90,
                    "dx": 0.25,
                    "dy": 0.25,
                    "parameterCategory": 2,
                    "parameterNumber": 2
                },
                "data": array
            }
        }
        return data


def read_mfwam25_seawaveheight_nc(input_path, since_time=datetime.strptime("1950010100", "%Y%m%d%H")):
    try:
        with Dataset(input_path) as nc_obj:
            time_li = (nc_obj.variables['time'][:])
            latitude_li = (nc_obj.variables['latitude'][:])
            longitude_li = (nc_obj.variables['longitude'][:])

            values_array = []
            for value_name in ["VHM0"]:
                try:
                    value_li = np.array(nc_obj[value_name][:])
                except Exception as e:
                    logging.error(
                        f"=> Mfwam25 not find {value_name} in {input_path}")
                    yield None
                missing_value = get_default_value(nc_obj, value_name)
                values_dict = {'value_name': value_name,
                               'value_li': value_li, 'missing_value': missing_value}
                values_array.append(values_dict)
    except Exception as e:
        logging.error(f"=> mfwam25 没有该文件：{input_path}")
        yield None
    else:

        for time_index in range(0, len(time_li)):
            array = []
            delta_hour = int(time_li[time_index])
            dt = since_time + timedelta(hours=delta_hour)
            # utc_time = dt + timedelta(hours=+8)
            # timestamp = int(time.mktime(utc_time.timetuple())) * 1000
            # print(f"{since_time}, {delta_hour} => {dt}")
            for lat_index in range(0, len(latitude_li)):
                for lon_index in range(0, len(longitude_li)):
                    for value_dict in values_array:
                        value_name = value_dict['value_name']
                        value = float(
                            value_dict['value_li'][time_index][lat_index][lon_index])
                        missing_value = value_dict['missing_value']
                        # if value == missing_value:
                        #     continue
                        array.append(round(value, 2))
            print(">>> array 长度", len(array), len(
                latitude_li), len(longitude_li))
            data = {
                "dt": dt.strftime("%Y%m%d%H"),
                "data": {"array": array, "latLgh": len(latitude_li), "lonLgh": len(longitude_li)}
            }
            yield data


def sync_redis(rds, date, elem, value):
    try:
        key = f"{elem}:{date}"
        value = value
        res = rds.rds.set(key, value)
        logging.info(f"set ok, res: {res}")
    except Exception as e:
        logging.info(f"set failed, res: {str(e)}")
