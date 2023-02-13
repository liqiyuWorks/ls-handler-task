from netCDF4 import Dataset
from datetime import datetime
import numpy as np

def get_default_value(nc_obj, value_name):
    attributes = nc_obj[value_name].ncattrs()
    if 'missing_value' in attributes:
        return nc_obj[value_name].getncattr('missing_value')
    else:
        return nc_obj[value_name].getncattr('_FillValue')


def read_gfs_nc(input_path):
    with Dataset(input_path) as nc_obj:
        # print(f"> 文件时间: {date_str} => {delta_hour}")
        print(nc_obj)
        latitude_li=(nc_obj.variables['lat_0'][:])
        longitude_li=(nc_obj.variables['lon_0'][:])
        values_array = []
        # for value_name in ["PRES_P0_L1_GLL0"]:
        for value_name in ["Pressure_reduced_to_MSL_msl"]:
            try:
                value_li = np.array(nc_obj[value_name][:])
            except Exception as e:
                return None
            missing_value = get_default_value(nc_obj, value_name)
            values_dict = {'value_name': value_name, 'value_li': value_li, 'missing_value': missing_value}
            values_array.append(values_dict)
        
        array = []
        for lat_index in range(0, len(latitude_li)):
            for lon_index in range(0, len(longitude_li)):
                for value_dict in values_array:
                    value_name = value_dict['value_name']
                    value = float(value_dict['value_li'][lat_index][lon_index])
                    missing_value = value_dict['missing_value']
                    # if value == missing_value:
                    #     continue
                    array.append(round(value,2))
        
        print(">>> array 长度", len(array),len(latitude_li), len(longitude_li))
 
 
if __name__ == '__main__':
    input_path = "/Users/jiufangkeji/Documents/JiufangCodes/jiufang-work/NC文件/GFS/gfs_2022080118.f159.nc"
    # input_path = "/Users/jiufangkeji/Desktop/gfs.t18z.pgrb2.0p25.f006.nc"
    read_gfs_nc(input_path)

     