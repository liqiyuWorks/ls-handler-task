#from scipy.misc import imread
import logging
import time
import requests
from PIL import Image
from io import BytesIO
import numpy as np
import sys, os
import imageio
import pymongo
from netCDF4 import Dataset
from datetime import datetime, timedelta
from random import randint
PREP_WEIGHT = "http://cdn.caiyunapp.com/weather/radar/cnweight_raw_"
WEIGHT_NAME = "cnweight_raw_"
PREP_URL = "http://cdn.caiyunapp.com/weather/radar/"

USER_AGENTS = [
 "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
 "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; Acoo Browser; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)",
 "Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
 "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)",
 "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
 "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
 "Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.2; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 3.0.04506.30)",
 "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)",
 "Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6",
 "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
 "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
 "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5",
 "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6",
 "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
 "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
 "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; fr) Presto/2.9.168 Version/11.52",
]

headers = {
            'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding':'gzip, deflate',  # 重要
            'accept-language':'zh,zh-CN;q=0.9,en-US;q=0.8,en;q=0.7',   # 重要
            'Cache-Control': 'max-age=0',
            'Connection' : 'keep-alive',
            'Host': 'cdn.caiyunapp.com',
            'Upgrade-Insecure-Requests':'1',
            'Cookie': '_oct_rt_id.8c2b=296b17a3-2620-4b4a-a134-8ce111a195a5.1631774109.1.1631774131.1631774109.734f8c35-da5d-404f-82b8-07e221ec8e24; _pk_id.5.8c2b=7e460e159fc1498a.1632894317.5.1634866678.1634713125.; _dd_s=logs=1&id=5b164d99-3922-46cb-971a-409360c22101&created=1651037129890&expire=1651038084826',
            'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4530.0 Safari/537.36'
        }

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

def format_time(india_time_str, india_format='%Y%m%d%H%M',hours=8):
    india_dt = datetime.strptime(india_time_str, india_format)
    local_dt = india_dt + timedelta(hours=hours)
    # local_format = "%Y-%m-%d %H:%M:%S"
    # time_str = local_dt.strftime(local_format)
    return local_dt

def is_none(s):
    if s is None:
        return True
    flag = False
    if isinstance(s, str):
        if len(s.strip()) == 0:
            flag = True
        if s == '-':
            flag = True
    elif isinstance(s, list):
        if len(s) == 0:
            flag = True
    elif isinstance(s, dict):
        flag = True
        for v in s.values():
            if is_none(v):
                continue
            flag = False
            break
    return flag


def get_mgo():
    # 数据库源连接
    mongo_host = os.getenv('MONGO_HOST', '119.3.248.125')
    mongo_port = int(os.getenv('MONGO_PORT', '21617'))
    mongo_db = os.getenv('MONGO_DB', 'cma')

    if mongo_db is None:
        return None, None
    url = 'mongodb://{}:{}/'.format(mongo_host, mongo_port)
    mgo_client = pymongo.MongoClient(url)

    mgo_db = mgo_client[mongo_db]
    mongo_user = os.getenv('MONGO_USER', 'reader')
    mongo_password = os.getenv('MONGO_PASSWORD', 'Read1234')

    if mongo_user is not None:
        mgo_db.authenticate(mongo_user, mongo_password)
    return mgo_client, mgo_db


lats = [3.9079, 57.9079]
lngs = [71.9282, 150.6026]
VALID = 255
NORM = 255


def latlng2xy(data, lat, lng):
    lat_size, lng_size = data.shape  # (6000, 7500)
    y = int((lng - lngs[0]) / (lngs[1] - lngs[0]) * lng_size)
    x = int((lats[1] - lat) / (lats[1] - lats[0]) * lat_size)
    return x, y


def radar_rain2precip_metric(intn):
    intn[intn > 0] = intn[intn > 0] + 0.15
    val = intn * 16.0 * 5
    dbz = 70 * (val > 70) + val * (val <= 70)
    val = np.power(np.power(10.0, dbz / 10.0) / 200, 5.0 / 8.0)
    val = val - 0.2051
    precip = val * (val > 0)
    return precip


class MgoStore(object):
    def __init__(self, config):
        self.config = config
        # 连接对象
        self.mgo_client = config['mgo_client']
        self.mgo_db = config['mgo_db']

        # 字符串
        self.collection = config['collection']
        self.mgo_coll = self.mgo_db[self.collection]
        # 唯一索引列
        self.uniq_idx = config['uniq_idx']
        # 常规索引名称和索引列 字典
        self.idx_dic = config.get('idx_dic', {})

        # 检查索引是否创建
        index_dic = self.mgo_coll.index_information()
        self.mgo_coll.create_index(self.uniq_idx,
                                   unique=True,
                                   name='{}_uniq_idx'.format(self.collection))
        for idx_name, idx in self.idx_dic.items():
            if idx_name in index_dic:
                continue
            self.mgo_coll.create_index(idx, name=idx_name)

    def set(self, key, data, extra=None):
        response = None
        try:
            query = {}
            if is_none(key):
                for field_tuple in self.uniq_idx:
                    field = field_tuple[0]
                    query[field] = data[field]
            else:
                query = key
            if extra is not None and 'op' in extra:
                op = extra['op']
            else:
                op = '$set'
            res = self.mgo_coll.update_one(query, {op: data}, upsert=True)
            if res.raw_result['updatedExisting']:
                if res.raw_result['nModified'] > 0:
                    logging.info('update {}'.format(data))
                else:
                    logging.info('nothing to update for key {}'.format(query))
            elif 'upserted' in res.raw_result:
                logging.info('insert {} {}'.format(res.raw_result['upserted'],
                                                   data))
            else:
                logging.info('impossible update_one result {}'.format(
                    res.raw_result))
            response = res.raw_result
        except pymongo.errors.DuplicateKeyError:
            # 索引建对了，就不会走到这个分支
            logging.info('duplicate key {}'.format(key))
        except Exception as e:
            logging.error('key {} data {}'.format(key, data))
            logging.error(e)
            return response
        return response

    def get(self, key, extra=None):
        response = {}
        try:
            if isinstance(extra, dict) and 'out_fileds' in extra:
                out_fields = extra['out_fields']
            else:
                out_fields = {'_id': 0}
            res = self.mgo_coll.find_one(key, out_fields)
            if res is not None:
                response = res
        except Exception as e:
            print(e)
            return response
        return response

    def close(self):
        self.mgo_client.close()


def write_caiyun_mgo(INPUT_PATH):
    # print(INPUT_PATH,UTC_date_time)
    for (dir_path, dir_names, file_names) in os.walk(INPUT_PATH):
        print(file_names)
        if not file_names:
            continue
        cnweight = [
            x for i, x in enumerate(file_names) if x.find('cnweight') != -1
        ]
        cnmap_precp = [
            x for i, x in enumerate(file_names) if x.find('cnmap_precp') != -1
        ]
        if cnweight:
            cnweight = cnweight[0]
        else:
            logging.error('该目录无cnweight_raw_图片')
            
        if cnmap_precp:
            cnmap_precp = cnmap_precp[0]
        UTC_date_time = datetime.strptime(cnmap_precp[12:24],"%Y%m%d%H%M")
        print(UTC_date_time)
        
        cnweight_path = os.path.join(dir_path, cnweight)
        print(cnweight_path)

        for tm in range(24):
            nt = tm * 5
            time2 = UTC_date_time + timedelta(minutes=nt)
            nametime = time2.strftime("%Y%m%d%H%M")
            # print(nametime)
            filename = cnmap_precp[:25] + nametime + cnmap_precp[37:]
            # print(filename)
            file_path = os.path.join(dir_path, filename)
            print(file_path)
            data = imageio.imread(file_path)
            weight = imageio.imread(cnweight_path)
            prep = np.zeros((21, 21))

            lon0 = 112.0
            lat0 = 31.7
            for ii in range(21):
                for jj in range(21):
                    lon = lon0 + ii * 0.01
                    lat = lat0 + jj * 0.01
                    x, y = latlng2xy(data, lat, lon)

                    if weight[x, y] == VALID:
                        result = float(data[x, y]) / NORM
                    else:
                        result = 0
                    prep[ii, jj] = result
                    # print(lon, lat, result)

            precip = radar_rain2precip_metric(prep)
            lonx = np.linspace(112.0, 112.2, 21)
            laty = np.linspace(31.7, 31.9, 21)
            np_precip = np.array(precip)
            for i, lon in enumerate(lonx):
                for j, lat in enumerate(laty):
                    lon = round(lon, 2)
                    lat = round(lat, 2)
                    precip = np_precip[i, j]
                    dataTime = (time2 + timedelta(hours=8)).strftime("%Y%m%d%H%M")
                    yield {
                        "dataTime": dataTime,
                        "lon": lon,
                        "lat": lat,
                        "precip": precip
                    }


def read_his_prer_nc(input_path):
    for (dir_path, dir_names, file_names) in os.walk(input_path):
        print(dir_names)
        for dir_name in dir_names:
            now_date_time = dir_name
            file = input_path + dir_name + "/prer.nc"
            nc_obj = Dataset(file)
            # #读取数据值
            since_time = datetime.strptime(now_date_time,"%Y%m%d%H%M")
            time_li=(nc_obj.variables['time'][:])
            latitude_li=(nc_obj.variables['grid_yt'][:])
            longitude_li=(nc_obj.variables['grid_xt'][:])
            prer=(nc_obj.variables['prer'][:])
            # print(lat)
            # print(lon)
            print('---------------******-------------------')
            # print(prer)

            values_array = []
            for value_name in ["prer"]:
                value_li = np.array(nc_obj[value_name][:])
                missing_value = get_default_value(nc_obj, value_name)
                values_dict = {'value_name': value_name, 'value_li': value_li, 'missing_value': missing_value}
                values_array.append(values_dict)

            for time_index in range(0, len(time_li)):
                hour = int(time_li[time_index])
                day = since_time + timedelta(hours=hour)
                for lat_index in range(0, len(latitude_li)):
                    lat = latitude_li[lat_index]
                    for lon_index in range(0, len(longitude_li)):
                        lon = longitude_li[lon_index] - 360 if longitude_li[lon_index] > 180 else longitude_li[lon_index]
                        data = {
                        'dataTime': day.strftime('%Y%m%d%H'),
                        'latitude': '%.02f' % lat,
                        'longitude': '%.02f' % lon,
                        }
                        for value_dict in values_array:
                            value_name = value_dict['value_name']
                            value = float(value_dict['value_li'][time_index][lat_index][lon_index])
                            missing_value = value_dict['missing_value']
                            if value == missing_value:
                                continue
                            data[value_name] = round(value,2)
                            yield data

def read_real_prer_nc(input_path, date_time):
    file = input_path + date_time + "/prer.nc"
    try:
        nc_obj = Dataset(file)
    except FileNotFoundError as e:
        logging.error('文件不存在')
        return 
    # #读取数据值
    since_time = datetime.strptime(date_time,"%Y%m%d%H%M")
    time_li=(nc_obj.variables['time'][:])
    latitude_li=(nc_obj.variables['grid_yt'][:])
    longitude_li=(nc_obj.variables['grid_xt'][:])
    prer=(nc_obj.variables['prer'][:])
    print('---------------******-------------------')

    values_array = []
    for value_name in ["prer"]:
        value_li = np.array(nc_obj[value_name][:])
        missing_value = get_default_value(nc_obj, value_name)
        values_dict = {'value_name': value_name, 'value_li': value_li, 'missing_value': missing_value}
        values_array.append(values_dict)

    for time_index in range(0, len(time_li)):
        hour = int(time_li[time_index])
        day = since_time + timedelta(hours=hour)
        for lat_index in range(0, len(latitude_li)):
            lat = latitude_li[lat_index]
            for lon_index in range(0, len(longitude_li)):
                lon = longitude_li[lon_index] - 360 if longitude_li[lon_index] > 180 else longitude_li[lon_index]
                data = {
                'dataTime': day.strftime('%Y%m%d%H'),
                'latitude': '%.02f' % lat,
                'longitude': '%.02f' % lon,
                }
                for value_dict in values_array:
                    value_name = value_dict['value_name']
                    value = float(value_dict['value_li'][time_index][lat_index][lon_index])
                    missing_value = value_dict['missing_value']
                    if value == missing_value:
                        continue
                    data[value_name] = round(value,2)
                    yield data


def supplement_png_mgo(INPUT_PATH):
    files = os.listdir(INPUT_PATH)
    print(files)
    for fi in files:
        if '.DS_Store' in fi:
            continue
        print("=",fi)
        dir_path = os.path.join(INPUT_PATH,fi)
        files = os.listdir(dir_path)
        for file in files:
            par_dir_path = os.path.join(dir_path,file)
            print("==",par_dir_path)
            file_names = os.listdir(par_dir_path)
            print('\n')
            # print(file_names)
            # print(file)
            now_date_time = file
            cnmap_precp = [
                x for i, x in enumerate(file_names) if x.find('cnmap_precp') != -1
            ]
            if cnmap_precp:
                cnmap_precp = cnmap_precp[0]
            head = cnmap_precp[:25]
            tail = cnmap_precp[37:]
            
            if len(file_names) < 26:
                UTC_date_time =format_time(now_date_time,hours=-8)
                print(UTC_date_time)
                weight_png = PREP_WEIGHT + head[12:-1] + "_" + head[12:-1] +tail
                print(weight_png)
                response = requests.get(weight_png)
                weight = imageio.imread(BytesIO(response.content))
                for tm in range(24):
                    nt = tm * 5
                    time2 = UTC_date_time + timedelta(minutes=nt)
                    nametime = time2.strftime("%Y%m%d%H%M")
                    # print(nametime)
                    filename = cnmap_precp[:25] + nametime + cnmap_precp[37:]
                    request_png = PREP_URL + filename
                    response = requests.get(request_png)
                    data = imageio.imread(BytesIO(response.content))
                    prep = np.zeros((21, 21))

                    lon0 = 112.0
                    lat0 = 31.7
                    for ii in range(21):
                        for jj in range(21):
                            lon = lon0 + ii * 0.01
                            lat = lat0 + jj * 0.01
                            x, y = latlng2xy(data, lat, lon)

                            if weight[x, y] == VALID:
                                result = float(data[x, y]) / NORM
                            else:
                                result = 0
                            prep[ii, jj] = result
                            # print(lon, lat, result)

                    precip = radar_rain2precip_metric(prep)
                    lonx = np.linspace(112.0, 112.2, 21)
                    laty = np.linspace(31.7, 31.9, 21)
                    np_precip = np.array(precip)
                    for i, lon in enumerate(lonx):
                        for j, lat in enumerate(laty):
                            lon = round(lon, 2)
                            lat = round(lat, 2)
                            precip = np_precip[i, j]
                            dataTime = (time2 + timedelta(hours=8)).strftime("%Y%m%d%H%M")
                            yield {
                                "dataTime": dataTime,
                                "lon": lon,
                                "lat": lat,
                                "precip": precip
                            }


def func_request_png(url):
    flag = True
    while flag:
        try:
            data = requests.get(url=url,headers=headers).content
            flag = False
        except Exception as e:
            print('请求错误,暂停1min')
            time.sleep(60)
    return data

def supplement_request2png(INPUT_PATH,START_DATE,END_DATE,SLEEP_INTERVAL):
    files = os.listdir(INPUT_PATH)
    print(files)
    for fi in files:
        if '.DS_Store' in fi:
            continue
        print("=",fi)
        if fi > START_DATE and fi < END_DATE:
            dir_path = os.path.join(INPUT_PATH,fi)
            files = os.listdir(dir_path)
            for file in files:
                par_dir_path = os.path.join(dir_path,file)
                print("==",par_dir_path)
                file_names = os.listdir(par_dir_path)
                # print(file_names)
                # print(file)
                now_date_time = file
                cnmap_precp = [
                    x for i, x in enumerate(file_names) if x.find('cnmap_precp') != -1
                ]
                if cnmap_precp:
                    cnmap_precp = cnmap_precp[0]
                head = cnmap_precp[:25]
                tail = cnmap_precp[37:]
                
                if len(file_names) < 26:
                    UTC_date_time =format_time(now_date_time,hours=-8)
                    print(UTC_date_time)
                    weight_png = PREP_WEIGHT + head[12:-1] + "_" + head[12:-1] +tail
                    print(weight_png)
                    weoght_data = func_request_png(weight_png)

                    file_path = os.path.join(par_dir_path,WEIGHT_NAME+head[12:-1] + "_" + head[12:-1] +tail)
                    print(file_path)
                    check_create_path(file_path)
                    with open(file_path, 'wb') as f:
                        f.write(weoght_data)
                    print(f'{file_path} write ok')
                    for tm in range(24):
                        nt = tm * 5
                        time2 = UTC_date_time + timedelta(minutes=nt)
                        nametime = time2.strftime("%Y%m%d%H%M")
                        # print(nametime)
                        filename = cnmap_precp[:25] + nametime + cnmap_precp[37:]
                        request_png = PREP_URL + filename
                        file_path = os.path.join(par_dir_path,filename)
                        if not os.path.exists(file_path):
                            time.sleep(SLEEP_INTERVAL)
                            random_agent = USER_AGENTS[randint(0, len(USER_AGENTS)-1)]
                            headers["User-Agent"] = random_agent
                            png_data = func_request_png(request_png)
                            check_create_path(file_path)

                            # 将下载到的图片数据写入文件
                            with open(file_path, 'wb') as f:
                                f.write(png_data)
                            print(f'{file_path} write ok')


