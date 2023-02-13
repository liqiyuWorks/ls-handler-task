# python generator.py -q local_nc2redis:gfs --file_path /Users/jiufangkeji/Desktop/NC文件/GFS/gfs_2022080118.f159.nc
# python3 generator.py -q nc2redis:gfs --file_path /hpcdata/data_service/forecast/GFS/2022090106 --redis_host 124.70.86.179 --redis_port 21606 --redis_password Rds123
import argparse
import os.path
import json
import subprocess
import requests


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
    parser.add_argument("--file_path", help="input path", required=True)
    parser.add_argument("--file_type", help="gfs", required=True, default="gfs")
    parser.add_argument("--file_re", help="file regular expression", default="*")
    args = parser.parse_args()
    files = get_files(args.file_path, args.file_re)
    sorted_files = sorted(files)
    for file in sorted_files:
        task = {
            'type': args.file_type,
            'input_file': file
        }
        res = requests.post("http://124.70.86.179:21631/api/v2/file",json=task)
        print(f"task: {task} => res: {res.json()}")


if __name__ == "__main__":
    main()
