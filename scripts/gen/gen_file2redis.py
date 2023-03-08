# python3 gen_file2redis.py -q handler_convert_gfs_wind_nc2json_obs --file_path /data2/data_service/api/gfs/2023010100 --file_re "202301" --redis_host 139.9.115.225 --redis_port 21604 --redis_password Rds123
# python3 gen_file2redis.py -q handler_convert_era5_wind_nc2json_obs --file_path /hpcdata/data_service/history/ERA5/0p25/20220718/ --file_re "202207" --redis_host 192.168.0.200 --redis_port 21604 --redis_password Rds123
import argparse
import os.path

import redis
import json
import subprocess


def get_dir_files(file_path, filter_re):
    if filter_re == "*":
        filter_re = ""
    cmd = '/usr/bin/ls {} |grep "{}"'.format(file_path, filter_re)
    print('cmd {}'.format(cmd))
    res_dir_list = subprocess.getstatusoutput(cmd)
    if res_dir_list[1]:
        print('execute {} result {}'.format(cmd, res_dir_list))
        res_dir_list = res_dir_list[1].split('\n')
    else:
        res_dir_list = []
    files_list = []
    for dir in res_dir_list:
        if not os.path.isdir(os.path.join(file_path, dir)):
            files_list.append(os.path.join(file_path, dir))
        else:
            for root, dirs, files in os.walk(os.path.join(file_path, dir)):
                for file in files:
                    path = os.path.join(root, file)
                    files_list.append(path)
    return files_list


def get_files(file_path, filter_re):
    cmd = '/usr/bin/find {} -type f -name "{}"'.format(file_path, filter_re)
    print('cmd {}'.format(cmd))
    res = subprocess.getstatusoutput(cmd)
    if res[0] != 0 or len(res[1]) == 0:
        print('execute {} result {}'.format(cmd, res))
        return []
    files = res[1].split('\n')
    return files


def get_preday_files(file_path, filter_re):
    files = get_files(file_path, filter_re)
    pre_files = []
    for file in files:
        file_name = os.path.basename(file)
        splits = file_name.rstrip(".nc").split('_')
        pre_day = splits[-2]
        cur_day = splits[-1].strip('R')
        if pre_day < cur_day:
            pre_files.append(file)
    return pre_files


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, width=200),
                                     description="""example:
  python3 generator.py -q gfs --file_path ./data
""")
    parser.add_argument("-q", "--queue", help="queue name", required=True)
    parser.add_argument("--file_path", help="input path", required=True)
    parser.add_argument("--file_re", help="file regular expression", default="*")
    parser.add_argument("--redis_host", help="redis host", default="124.70.86.179")
    parser.add_argument("--redis_port", help="redis port", default="21605")
    parser.add_argument("--redis_password", help="redis password", default="Rds123")
    parser.add_argument("--cur_year", help="cur year or not", default="no")
    args = parser.parse_args()

    rds = redis.Redis(host=args.redis_host, port=args.redis_port, db=0, password=args.redis_password,
                      decode_responses=True)
    if args.cur_year == "yes":
        files = get_preday_files(args.file_path, args.file_re)
    else:
        if(os.path.isdir(args.file_path)):
            files = get_dir_files(args.file_path, args.file_re)
        else:
            files = get_files(args.file_path, args.file_re)
    sorted_files = sorted(files)
    print(sorted_files)
    for file in sorted_files:
        task = {
            'task_type': args.queue,
            'input_file': file
        }
        queue_len = rds.rpush(args.queue, json.dumps(task))
        print("queue {} length {}, new task {}".format(args.queue, queue_len, task))


if __name__ == "__main__":
    # 
    main()
