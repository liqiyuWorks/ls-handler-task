import requests
from datetime import datetime, timedelta
from datetime import timezone
from clickhouse_driver import Client
from pkg.public.convert import convert_era5_wave_point, convert_era5_wind_point, convert_era5_flow_point
import math
import traceback


def request_mmsi_details(mmsi):
    try:
        url = "https://api.navgreen.cn/api/vessel/details"

        querystring = {"mmsi": mmsi}

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
    except Exception as e:
        traceback.print_exc()

    return response.json().get("data", [])


def is_valid_type(s):
    try:
        if s != "" and s != None:
            return True
    except (ValueError, TypeError):
        return False


def deal_list(data, DESIGN_DRAFT, DESIGN_SPEED):
    """
    处理船舶数据列表，计算符合条件的平均船速（优化版）
    新增功能：根据吃水(draft)区分空载(<60%)和满载(>80%)船速
    """
    # 设计吃水深度阈值
    EMPTY_LOAD = DESIGN_DRAFT*0.7  # 60%
    FULL_LOAD = DESIGN_DRAFT*0.8   # 80%

    # 第一阶段：强化初步筛选（过滤无效值并预转换类型）
    filtered = (
        d for d in data
        if is_valid_type(d.get("wind_level"))
        and is_valid_type(d.get("wave_height"))
        and is_valid_type(d.get("hdg"))
        and is_valid_type(d.get("sog"))
        and is_valid_type(d.get("draught"))  # 新增吃水有效性检查
        and int(d.get("wind_level", 5)) <= 4
        and float(d.get("wave_height", 1.26)) <= 1.25
        and float(d.get("sog", 0.0)) >= DESIGN_SPEED*0.5
    )

    # 第二阶段：分别统计空载和满载数据
    empty_total = 0.0
    empty_count = 0
    full_total = 0.0
    full_count = 0
    
    is_sailing_downstream_true = []
    is_sailing_downstream_false = []

    for item in filtered:
        try:
            # 单次字典遍历提取所有字段（减少字典访问次数）
            draft = float(item["draught"])  # 获取吃水值
            speed = float(item["sog"])
            hdg = float(item["hdg"])
            if is_sailing_downstream(
                item["u_wind"], item["v_wind"], hdg):
                is_sailing_downstream_true.append(item)
            else:
                is_sailing_downstream_false.append(item)

            # 根据吃水比例分类统计
            if draft < EMPTY_LOAD:
                empty_total += speed
                empty_count += 1
            elif draft > FULL_LOAD:
                full_total += speed
                full_count += 1

        except (ValueError, KeyError) as e:
            print(f"数据异常跳过: {e}")
            continue

    # 计算各类平均速度
    avg_empty_speed = round(empty_total / empty_count,
                            2) if empty_count else 0.0
    avg_full_speed = round(full_total / full_count, 2) if full_count else 0.0
    avg_good_weather_speed = round((empty_total + full_total) / (
        empty_count + full_count), 2) if (empty_count + full_count) else 0.0

    performance = {
        "avg_good_weather_speed": avg_good_weather_speed,
        # "avg_ballast_speed": avg_empty_speed,  # 空载平均速度
        # "avg_laden_speed": avg_full_speed,    # 满载平均速度
        # "empty_load_count": empty_count,          # 空载数据计数
        # "full_load_count": full_count             # 满载数据计数
    }

    print("空载水深是", EMPTY_LOAD, "，空载匹配个数是", empty_count, "，满载匹配个数是", full_count)
    if empty_count:
        performance["avg_ballast_speed"] = avg_empty_speed

    if full_count:
        performance["avg_laden_speed"] = avg_full_speed

    return performance


class ClickHouseClient:
    def __init__(self, host='123.249.97.59', port=21663, user='default',
                 password='shipping_history123', database='shipping_history'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.client = None
        self.connect()

    def connect(self):
        """建立数据库连接"""
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                database=self.database,
                password=self.password,
                send_receive_timeout=5
            )
            print("> ClickHouse client connected successfully")
        except Exception as e:
            print(f"Error connecting to ClickHouse: {e}")
            raise

    def query(self, sql):
        """执行 SQL 查询

        Args:
            sql (str): SQL 查询语句

        Returns:
            list: 查询结果
        """
        try:
            return self.client.execute(sql)
        except Exception as e:
            print(f"Error executing query: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.disconnect()
            print("> ClickHouse client disconnected")


def get_vessel_track(mmsi, start_time, end_time):
    """
    根据船舶 mmsi 和时间，读取船舶的航行轨迹

    Args:
        mmsi (str): 船舶的MMSI号
        start_time (str): 开始时间，格式：YYYY-MM-DD HH:MM:SS
        end_time (str): 结束时间，格式：YYYY-MM-DD HH:MM:SS

    Returns:
        dict: API返回的JSON响应
    """
    url = "https://api.navgreen.cn/api/vessel/status/track"

    params = {
        "mmsi": mmsi,
        "status": 0,
        "start_time": start_time,
        "end_time": end_time
    }

    headers = {
        "accept": "application/json",
        "token": "NAVGREEN_ADMIN_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjE1MDAxNTMsInVzZXJuYW1lIjoiaml1ZmFuZyIsImFjY2Vzc19rZXkiOiJMUzhBOUVGMTk2NDFGQkI1Q0Q4QUI3RUZFMjVGMUE3NSIsInNlY3JldF9rZXkiOiJMUzQzQkMzRUIzNkMyMzNDRDI0QTYwN0EzRkVDQUIxOCJ9.8zYU58Mxfiu-GDpOEGva1iGzxA0Dyexw1FoGfrdIrtc"
    }

    response = requests.get(url, params=params, headers=headers)
    track_data = response.json().get("data", {}).get("data", [])
    # 1. 解析postime为datetime，假定为北京时间
    for point in track_data:
        point["postime_dt"] = datetime.strptime(
            point.get("postime"), "%Y-%m-%d %H:%M:%S")
        # 假定原始时间为北京时间（UTC+8）
        point["postime_dt"] = point["postime_dt"].replace(
            tzinfo=timezone(timedelta(hours=8)))
    # 2. 按时间排序
    track_data.sort(key=lambda x: x["postime_dt"])
    # 3. 以1小时为间隔重采样
    resampled = []
    last_time = None
    for point in track_data:
        if last_time is None or (point["postime_dt"] - last_time).total_seconds() >= 3600:
            resampled.append(point)
            last_time = point["postime_dt"]
    # 4. 对齐到最近的3小时整点，并去重
    aligned = {}
    for point in resampled:
        dt_utc = point["postime_dt"].astimezone(timezone.utc)
        # 计算最近的3小时整点
        hour = round(dt_utc.hour / 3) * 3
        if hour == 24:
            dt_utc = dt_utc.replace(hour=0) + timedelta(days=1)
            hour = 0
        aligned_time = dt_utc.replace(
            hour=hour, minute=0, second=0, microsecond=0)
        key = aligned_time.strftime("%Y-%m-%d %H:%M:%S")
        if key not in aligned:
            aligned[key] = {
                "lon": point.get("lon"),
                "lat": point.get("lat"),
                "sog": point.get("sog"),
                "cog": point.get("cog"),
                "hdg": point.get("hdg"),
                "draught": point.get("draught"),
                "postime": key
            }
    track_data = list(aligned.values())
    track_data.sort(key=lambda x: x["postime"])  # 按时间排序
    # 修复hdg为None
    for point in track_data:
        if point.get("hdg") is None:
            if point.get("cog") is not None:
                point["hdg"] = point["cog"]
            else:
                point["hdg"] = 0
    return track_data


def handle_track_point_weather(i, ck_client):
    lon = i.get("lon")
    lat = i.get("lat")
    sog = i.get("sog")
    cog = i.get("cog")
    hdg = i.get("hdg")
    draught = i.get("draught")
    postime = i.get("postime")
    # 将时间转换为datetime对象
    print(lon, lat, sog, cog, hdg, draught, postime)

    lat_index, lon_index = convert_era5_wave_point(lat, lon)

    sql_ck = f"""
    SELECT *
    FROM shipping_history.era5_wave_0p5
    WHERE lat_index = {lat_index}
    AND lon_index = {lon_index} 
    AND history_date = toDateTime('{postime}')
    LIMIT 10
    """

    result = ck_client.query(sql_ck)
    print(result)


def batch_query_ck(client, sql_template, index_time_list, batch_size=500):
    results = []
    for i in range(0, len(index_time_list), batch_size):
        batch = index_time_list[i:i+batch_size]
        values_clause = ",\n".join(
            f"({lat},{lon},toDateTime('{postime}'))"
            for lat, lon, postime in batch
        )
        sql = sql_template.format(values=values_clause)
        results.extend(client.query(sql))
    return results


def fetch_era5_wave_for_track(track_data, ck_client, batch_size=500):
    # 1. 生成索引和时间元组，去重
    seen = set()
    index_time_list = []
    for point in track_data:
        lat = point["lat"]
        lon = point["lon"]
        postime = point["postime"]
        lat_index, lon_index = convert_era5_wave_point(lat, lon)
        key = (lat_index, lon_index, postime)
        if key not in seen:
            seen.add(key)
            index_time_list.append(key)
        point["lat_index"] = lat_index
        point["lon_index"] = lon_index

    # 2. SQL模板
    sql_template = """
    SELECT *
    FROM shipping_history.era5_wave_0p5
    WHERE (lat_index, lon_index, history_date) IN (
        {values}
    )
    """

    # 3. 分批查询
    results = batch_query_ck(ck_client, sql_template,
                             index_time_list, batch_size)

    # 4. 构建映射
    weather_map = {}
    for row in results:
        lat_index, lon_index, history_date = row[0], row[1], row[2]
        weather_map[(lat_index, lon_index, str(history_date))] = row

    # 5. 合并到track_data
    weather_keys = [
        "lat_index", "lon_index", "history_date",
        "wave_height", "wave_direction", "wave_period",
        "swell_wave_height", "swell_wave_direction", "swell_wave_period",
        "wind_wave_height", "wind_wave_direction", "wind_wave_period"
    ]
    for point in track_data:
        key = (point["lat_index"], point["lon_index"], point["postime"])
        weather = weather_map.get(key)
        if weather:
            for k, v in zip(weather_keys, weather):
                point[k] = v

    return track_data


def fetch_era5_wind_for_track(track_data, ck_client, batch_size=500):
    seen = set()
    index_time_list = []
    for point in track_data:
        lat = point["lat"]
        lon = point["lon"]
        postime = point["postime"]
        lat_index, lon_index = convert_era5_wind_point(lat, lon)
        key = (lat_index, lon_index, postime)
        if key not in seen:
            seen.add(key)
            index_time_list.append(key)
        point["wind_lat_index"] = lat_index
        point["wind_lon_index"] = lon_index

    sql_template = """
    SELECT *
    FROM shipping_history.era5_0p25
    WHERE (lat_index, lon_index, history_date) IN (
        {values}
    )
    """

    results = batch_query_ck(ck_client, sql_template,
                             index_time_list, batch_size)

    weather_map = {}
    for row in results:
        lat_index, lon_index, history_date = row[0], row[1], row[2]
        weather_map[(lat_index, lon_index, str(history_date))] = row

    weather_keys = [
        "wind_lat_index", "wind_lon_index", "wind_history_date",
        "pressure", "temperature", "u_wind", "v_wind"
    ]
    for point in track_data:
        key = (point["wind_lat_index"],
               point["wind_lon_index"], point["postime"])
        weather = weather_map.get(key)
        if weather:
            for k, v in zip(weather_keys, weather):
                point[k] = v
    return track_data


def fetch_era5_flow_for_track(track_data, ck_client, batch_size=500):
    seen = set()
    index_time_list = []
    for point in track_data:
        lat = point["lat"]
        lon = point["lon"]
        postime = point["postime"]
        lat_index, lon_index = convert_era5_flow_point(lat, lon)
        key = (lat_index, lon_index, postime)
        if key not in seen:
            seen.add(key)
            index_time_list.append(key)
        point["flow_lat_index"] = lat_index
        point["flow_lon_index"] = lon_index

    sql_template = """
    SELECT *
    FROM shipping_history.era5_flow_0p83
    WHERE (lat_index, lon_index, history_date) IN (
        {values}
    )
    """

    results = batch_query_ck(ck_client, sql_template,
                             index_time_list, batch_size)

    weather_map = {}
    for row in results:
        lat_index, lon_index, history_date = row[0], row[1], row[2]
        weather_map[(lat_index, lon_index, str(history_date))] = row

    weather_keys = [
        "flow_lat_index", "flow_lon_index", "flow_history_date",
        "u_flow", "v_flow"
    ]
    for point in track_data:
        key = (point["flow_lat_index"],
               point["flow_lon_index"], point["postime"])
        weather = weather_map.get(key)
        if weather:
            for k, v in zip(weather_keys, weather):
                point[k] = v
    return track_data


def merge_track_data(track_data, track_wave_data, track_wind_data, track_flow_data):
    # 1. 构建映射
    def build_map(data, lat_key, lon_key, time_key):
        return {
            (str(d[lat_key]), str(d[lon_key]), str(d[time_key])): d
            for d in data
        }

    wave_map = build_map(track_wave_data, "lat", "lon", "postime")
    wind_map = build_map(track_wind_data, "lat", "lon", "postime")
    flow_map = build_map(track_flow_data, "lat", "lon", "postime")

    merged = []
    for point in track_data:
        key = (str(point["lat"]), str(point["lon"]), str(point["postime"]))
        merged_point = point.copy()
        # 合并wave
        wave = wave_map.get(key)
        if wave:
            for k, v in wave.items():
                if k not in merged_point:
                    merged_point[k] = v
        # 合并wind
        wind = wind_map.get(key)
        if wind:
            for k, v in wind.items():
                if k not in merged_point:
                    merged_point[k] = v
        # 合并flow
        flow = flow_map.get(key)
        if flow:
            for k, v in flow.items():
                if k not in merged_point:
                    merged_point[k] = v
        merged.append(merged_point)
    return merged


def format_history_dates(data):
    for point in data:
        for key in ["history_date", "wind_history_date", "flow_history_date"]:
            if key in point and isinstance(point[key], datetime):
                point[key] = point[key].strftime("%Y-%m-%d %H:%M:%S")
    return data


def filter_fields(data):
    keep_keys = [
        "lon", "lat", "sog", "cog", "hdg", "draught", "postime",
        "wave_height", "wave_direction", "wave_period",
        "swell_wave_height", "swell_wave_direction", "swell_wave_period",
        "wind_wave_height", "wind_wave_direction", "wind_wave_period",
        "pressure", "temperature", "u_wind", "v_wind", "u_flow", "v_flow"
    ]
    return [
        {k: d[k] for k in keep_keys if k in d}
        for d in data
    ]


def calculate_wind_level(speed):
    if speed is None or math.isnan(speed):
        return 0
    if speed <= 0.2:
        return 0
    elif speed <= 1.5:
        return 1
    elif speed <= 3.3:
        return 2
    elif speed <= 5.4:
        return 3
    elif speed <= 7.9:
        return 4
    elif speed <= 10.7:
        return 5
    elif speed <= 13.8:
        return 6
    elif speed <= 17.1:
        return 7
    elif speed <= 20.7:
        return 8
    elif speed <= 24.4:
        return 9
    elif speed <= 28.4:
        return 10
    elif speed <= 32.6:
        return 11
    else:
        return 12


def convert_uv_wind_to_speed_and_angle(u, v):
    if u is None or v is None or math.isnan(u) or math.isnan(v):
        return 0.0, 0.0
    speed = math.sqrt(u ** 2 + v ** 2)
    angle = math.degrees(math.atan2(u, v))
    if angle > 0:
        angle = angle - 180
    else:
        angle = angle + 180
    return speed, angle


directions_list = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]


def convert_angle_to_direction(angle):
    if angle < 0:
        angle = 360 + angle
    if math.isnan(angle):
        return directions_list[0]
    index = int((angle + 11.25) / 22.5) % 16
    return directions_list[index]


def ms_to_kts(speed):
    if speed is None or math.isnan(speed):
        return 0.0
    return speed * 1.94384449


def enrich_wind_info(data):
    for point in data:
        u = point.get("u_wind")
        v = point.get("v_wind")
        if u is not None and v is not None:
            speed, angle = convert_uv_wind_to_speed_and_angle(u, v)
            level = calculate_wind_level(speed)
            direction = convert_angle_to_direction(angle)
            point["wind_speed"] = speed
            point["wind_angle"] = angle
            point["wind_level"] = level
            point["wind_direction"] = direction
            point["wind_speed_kts"] = ms_to_kts(speed)
    return data


def calculate_flow_degree(angle):
    if angle < 0:
        angle += 360.
    return angle


def convert_uv_flow_to_speed_and_angle(u, v):
    if u is None or v is None or math.isnan(u) or math.isnan(v):
        return 0.0, 0.0
    speed = math.sqrt(u ** 2 + v ** 2)
    angle = math.degrees(math.atan2(u, v))
    return speed, angle


def enrich_flow_info(data):
    for point in data:
        u = point.get("u_flow")
        v = point.get("v_flow")
        if u is not None and v is not None:
            speed, angle = convert_uv_flow_to_speed_and_angle(u, v)
            if speed > 0:
                angle = calculate_flow_degree(angle)
            else:
                angle = 0.0
            direction = convert_angle_to_direction(angle)
            point["flow_speed"] = speed
            point["flow_angle"] = angle
            point["flow_direction"] = direction
            point["flow_speed_kts"] = ms_to_kts(speed)
    return data


def is_sailing_downstream(u, v, ship_angle):
    """
    判断船舶是否顺流航行
    :param u: 洋流东向分量(m/s)
    :param v: 洋流北向分量(m/s)
    :param ship_angle: 船舶航向角(°)，从正北顺时针方向
    :return: 布尔值，True表示顺流，False表示逆流或横流
    """
    # 计算洋流方向角度（0°为正北，顺时针增加）
    current_angle = math.degrees(math.atan2(u, v)) % 360
    if current_angle < 0:
        current_angle += 360

    # 计算船舶航向与洋流方向的夹角差
    angle_diff = abs(ship_angle - current_angle)
    min_angle_diff = min(angle_diff, 360 - angle_diff)

    # 判断顺流条件（夹角≤45°视为顺流）[2,7](@ref)
    return min_angle_diff <= 45


# 使用示例
if __name__ == "__main__":
    mmsi = "414281000"
    details = request_mmsi_details(mmsi)
    draught, desgin_speed = details.get(
        "data")[0]["draught"], details.get("data")[0]["speed"]
    end_time = datetime.now()
    start_time = end_time - timedelta(days=90)  # 3个月 = 90天
    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
    print(start_time, end_time)
    track_data = get_vessel_track(mmsi, start_time, end_time)

    ck_client = ClickHouseClient()
    try:
        track_wave_data = fetch_era5_wave_for_track(
            track_data, ck_client)  # era5 wave
        track_wind_data = fetch_era5_wind_for_track(
            track_data, ck_client)  # era5 wind
        track_flow_data = fetch_era5_flow_for_track(
            track_data, ck_client)  # era5 flow
        merged_track_data = merge_track_data(
            track_data, track_wave_data, track_wind_data, track_flow_data)
        merged_track_data = format_history_dates(merged_track_data)
        filtered_track_data = filter_fields(merged_track_data)
        filtered_track_data = enrich_wind_info(filtered_track_data)
        filtered_track_data = enrich_flow_info(filtered_track_data)
        print(filtered_track_data[0])
        # 处理数据
        performance = deal_list(filtered_track_data, draught, desgin_speed)
        print(performance)

    finally:
        ck_client.close()
