from netCDF4 import Dataset
from datetime import datetime, timedelta
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
        latitude_li=(nc_obj.variables['lat_0'][:])
        longitude_li=(nc_obj.variables['lon_0'][:])
        values_array = []
        print(nc_obj.variables['UGRD_P0_L103_GLL0'])
        u_value_li = np.array(nc_obj['UGRD_P0_L103_GLL0'][:])
        v_value_li = np.array(nc_obj['VGRD_P0_L103_GLL0'][:])
        print(u_value_li[0][0][0])
        print(v_value_li[0][0][0])
        # print(nc_obj.variables['PRMSL_P0_L101_GLL0'])
        # print(nc_obj.variables['UGRD_P0_L103_GLL0'].ncattrs())
        # for value_name in ["UGRD_P0_L103_GLL0"]:
        #     try:
        #         value_li = np.array(nc_obj[value_name][:])
        #     except Exception as e:
        #         return None
        #     missing_value = get_default_value(nc_obj, value_name)
        #     values_dict = {'value_name': value_name, 'value_li': value_li, 'missing_value': missing_value}
        #     values_array.append(values_dict)
        
        # array = []
        # for lat_index in range(0, len(latitude_li)):
        #     for lon_index in range(0, len(longitude_li)):
        #         for value_dict in values_array:
        #             value_name = value_dict['value_name']
        #             value = float(value_dict['value_li'][lat_index][lon_index])
        #             missing_value = value_dict['missing_value']
        #             # if value == missing_value:
        #             #     continue
        #             array.append(round(value,2))
        
        # print(">>> array 长度", len(array),len(latitude_li), len(longitude_li))
        
        
def read_era5_nc(input_path):
    since_time=datetime.strptime("1900010100", "%Y%m%d%H")
    with Dataset(input_path) as nc_obj:
        # print(f"> 文件时间: {date_str} => {delta_hour}")
        latitude_li=(nc_obj.variables['latitude'][:])
        longitude_li=(nc_obj.variables['longitude'][:])
        time_li=(nc_obj.variables['time'][:])
        # print(nc_obj.variables['u10'])
        try:
            u10_li = np.array(nc_obj["u10"][:])
            v10_li = np.array(nc_obj["v10"][:])
        except Exception as e:
            return None
        values_dict = {'u10_li': u10_li, 'v10_li': v10_li}
        
        for ts_index in range(0, len(time_li)):
            array = []
            delta_hour = int(time_li[ts_index])
            dt = since_time + timedelta(hours=delta_hour)
            for lat_index in range(0, len(latitude_li)):
                for lon_index in range(0, len(longitude_li)):
                    u10 = float(values_dict['u10_li'][ts_index][lat_index][lon_index])
                    array.append(round(u10,2))
                    
            print(f">>> {dt}  {len(array)}  {len(latitude_li)}, {len(longitude_li)}")
            # break
                    
        
 
 
if __name__ == '__main__':
    # input_path = "/Users/jiufangkeji/Documents/JiufangCodes/jiufang-work/NC文件/GFS/2022121518/gfs.t18z.pgrb2.0p25.f360.nc"
    input_path = "/hpcdata/test/grib2nc/gfs/atmos/2023030600/gfs.t00z.pgrb2.0p25.f015.nc"
    read_gfs_nc(input_path)

     