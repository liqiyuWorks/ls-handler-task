import math

MFWAMHistoryStep = 1.0 / 12.0  # 等价于 Go 里的 float32(1. / 12.)


def convert_mfwam_point(lat: float, lon: float) -> "tuple[int, int]":
    """latitude: -80~90 longitude: -180~180 1 / 12"""
    lat_index = round((lat + 80.0) / MFWAMHistoryStep)
    lon_index = round((lon + 180.0) / MFWAMHistoryStep)

    if lon_index == 4320:
        lon_index = 0

    return int(lat_index), int(lon_index)


def convert_ec_point(lat: float, lon: float) -> "tuple[int, int]":
    """latitude: -90~90 longitude: -180~180 0.25"""
    ECHistoryStep = 0.25
    lat_index = round((lat + 90.0) / ECHistoryStep)
    lon_index = round((lon + 180.0) / ECHistoryStep)
    if lon_index == 1440:
        lon_index = 0
    return int(lat_index), int(lon_index)


def convert_smoc_point(lat: float, lon: float) -> "tuple[int, int]":
    """latitude: -80~90 longitude: -180~180 1/12"""
    SMOCHistoryStep = 1.0 / 12.0
    lat_index = round((lat + 80.0) / SMOCHistoryStep)
    lon_index = round((lon + 180.0) / SMOCHistoryStep)
    if lon_index == 4320:
        lon_index = 0
    return int(lat_index), int(lon_index)


def convert_era5_wind_point(lat: float, lon: float) -> "tuple[int, int]":
    """latitude: 90~-90, longitude: 0~360, 0.25"""
    lat_index = round((90.0 - lat) / 0.25)
    if lon >= 0:
        lon_index = round(lon / 0.25)
    else:
        lon_index = round((360.0 + lon) / 0.25)
    if lon_index == 1440:
        lon_index = 0
    return int(lat_index), int(lon_index)


def convert_era5_wave_point(lat: float, lon: float) -> "tuple[int, int]":
    """latitude: 90~-90, longitude: 0~360, 0.5"""
    lat_index = round((90.0 - lat) / 0.5)
    if lon >= 0:
        lon_index = round(lon / 0.5)
    else:
        lon_index = round((360.0 + lon) / 0.5)
    if lon_index == 720:
        lon_index = 0
    return int(lat_index), int(lon_index)


def convert_era5_flow_point(lat: float, lon: float) -> "tuple[int, int]":
    """latitude: -80~90, longitude: -180~180, 1/12"""
    SMOCHistoryStep = 1.0 / 12.0
    lat_index = round((lat + 80.0) / SMOCHistoryStep)
    lon_index = round((lon + 180.0) / SMOCHistoryStep)
    if lon_index == 4320:
        lon_index = 0
    return int(lat_index), int(lon_index)
